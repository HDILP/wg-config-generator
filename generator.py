"""Config generation orchestrator — wires keygen, templates, and file output."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from keygen import derive_pubkey, generate_keypair, KeyGenError
from models import GenerationConfig, KeyPair, PeerConfig, ServerConfig, ClientConfig
from templates import SERVER_CONF, CLIENT_CONF, PEER_BLOCK, README
from utils import ensure_dir, write_text, write_json, open_folder


# ── helpers shared by generate() and add_client() ────────────────

def _get_server_privkey(text: str) -> str:
    """Extract PrivateKey from [Interface] section of server.conf text."""
    m = re.search(r"^\s*PrivateKey\s*=\s*(\S+)", text, re.MULTILINE)
    if not m:
        raise ValueError("PrivateKey not found in server.conf")
    return m.group(1)


def _get_listen_port(text: str) -> int:
    """Extract ListenPort from server.conf text (default 51820)."""
    m = re.search(r"^\s*ListenPort\s*=\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else 51820


def _get_used_ips(text: str) -> set[str]:
    """Collect all IPs already used in [Peer] AllowedIPs."""
    ips: set[str] = set()
    for m in re.finditer(r"^\s*AllowedIPs\s*=\s*(\S+)", text, re.MULTILINE):
        ips.add(m.group(1).split("/")[0])
    return ips


def _next_client_ip(used: set[str]) -> str:
    """Pick the next available .2–.254 IP (ponytail: linear scan, fine for <253 clients)."""
    for i in range(2, 255):
        ip = f"10.66.66.{i}"
        if ip not in used:
            return ip
    raise RuntimeError("No available IPs in 10.66.66.0/24")


def _next_client_number(out_dir: Path) -> int:
    """Next sequential client number for file naming."""
    max_n = 1  # client.conf = #001
    for p in out_dir.glob("client_*.conf"):
        m = re.search(r"client_(\d+).conf", p.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    # also count bare client.conf
    if (out_dir / "client.conf").exists():
        max_n = max(max_n, 1)
    return max_n + 1


class ConfigGenerator:
    """Generates WireGuard server + client configs from user settings."""

    def __init__(self, cfg: GenerationConfig) -> None:
        self.cfg = cfg

    def generate(self) -> Dict[str, str]:
        """
        Full pipeline: generate keys → build configs → write files.

        Returns a dict with paths for post-generation display.
        """
        # 1. Generate key pairs
        server_keys = generate_keypair()
        client_keys = generate_keypair()

        # 2. Build config objects
        server_vpn = f"{self.cfg.server_vpn_ip}/24"
        client_vpn = f"{self.cfg.client_vpn_ip}/32"

        server = ServerConfig(
            private_key=server_keys.private,
            address=server_vpn,
            listen_port=self.cfg.listen_port,
            peers=[
                PeerConfig(
                    public_key=client_keys.public,
                    allowed_ips=client_vpn,
                )
            ],
        )

        endpoint = f"{self.cfg.server_public_ip}:{self.cfg.listen_port}"
        client = ClientConfig(
            private_key=client_keys.private,
            address=f"{self.cfg.client_vpn_ip}/24",
            server_public_key=server_keys.public,
            endpoint=endpoint,
            allowed_ips=self.cfg.vpn_subnet,
        )

        # 3. Output directory
        out = ensure_dir(self.cfg.output_dir)

        # 4. Write server.conf
        peers_section = "\n\n".join(
            PEER_BLOCK.format(public_key=p.public_key, allowed_ips=p.allowed_ips)
            for p in server.peers
        )
        write_text(
            out / "server.conf",
            SERVER_CONF.format(
                private_key=server.private_key,
                address=server.address,
                listen_port=server.listen_port,
                peers_section=peers_section,
            ),
        )

        # 5. Write client.conf
        write_text(
            out / "client.conf",
            CLIENT_CONF.format(
                private_key=client.private_key,
                address=client.address,
                server_public_key=client.server_public_key,
                endpoint=client.endpoint,
                allowed_ips=client.allowed_ips,
                persistent_keepalive=client.persistent_keepalive,
            ),
        )

        # 6. README
        write_text(
            out / "README.txt",
            README.format(
                server_public_ip=self.cfg.server_public_ip,
                server_vpn_ip=self.cfg.server_vpn_ip,
                client_vpn_ip=self.cfg.client_vpn_ip,
                listen_port=self.cfg.listen_port,
            ),
        )

        # 7. Human-readable public keys
        write_text(out / "server_public.txt", f"PublicKey = {server_keys.public}\n")
        write_text(out / "client_public.txt", f"PublicKey = {client_keys.public}\n")

        # 8. JSON key store (multi-client format)
        write_json(
            out / "keys.json",
            {
                "server": {"private": server_keys.private, "public": server_keys.public},
                "peers": [
                    {
                        "name": "client_001",
                        "private": client_keys.private,
                        "public": client_keys.public,
                        "ip": self.cfg.client_vpn_ip,
                    }
                ],
            },
        )

        return {
            "output_dir": str(out),
            "server_pubkey": server_keys.public,
            "client_pubkey": client_keys.public,
        }

    def generate_with_open(self) -> Dict[str, str]:
        """Generate configs and open the output folder."""
        result = self.generate()
        open_folder(ensure_dir(self.cfg.output_dir))
        return result

    # ── add client to existing server ────────────────────────────

    def add_client(
        self,
        server_conf_dir: str | Path,
        server_public_ip: str,
        client_vpn_ip: str | None = None,
        vpn_subnet: str = "10.66.66.0/24",
    ) -> Dict[str, str]:
        """
        Add a new client to an existing WireGuard server.

        server_conf_dir  — directory containing server.conf (and optionally keys.json)
        server_public_ip — public IP/domain for client endpoint
        client_vpn_ip    — override the auto-detected next IP

        Returns the same shape as generate().
        """
        out = ensure_dir(server_conf_dir)
        conf_path = out / "server.conf"
        if not conf_path.exists():
            raise FileNotFoundError(f"server.conf not found in {out}")

        text = conf_path.read_text(encoding="utf-8")

        # Existing server info
        server_priv = _get_server_privkey(text)
        server_pub = derive_pubkey(server_priv)
        listen_port = _get_listen_port(text)

        # Determine client IP
        used = _get_used_ips(text)
        if client_vpn_ip:
            if client_vpn_ip in used:
                raise ValueError(f"IP {client_vpn_ip} already in use by another peer")
        else:
            client_vpn_ip = _next_client_ip(used)

        # Generate keys
        client_keys = generate_keypair()
        client_number = _next_client_number(out)

        # Append [Peer] to server.conf
        new_block = (
            f"\n[Peer]\n"
            f"PublicKey = {client_keys.public}\n"
            f"AllowedIPs = {client_vpn_ip}/32\n"
        )
        conf_path.write_text(text.rstrip("\n") + new_block, encoding="utf-8")

        # Write client config
        name = f"client_{client_number:03d}"
        endpoint = f"{server_public_ip}:{listen_port}"
        write_text(
            out / f"{name}.conf",
            CLIENT_CONF.format(
                private_key=client_keys.private,
                address=f"{client_vpn_ip}/24",
                server_public_key=server_pub,
                endpoint=endpoint,
                allowed_ips=vpn_subnet,
                persistent_keepalive=25,
            ),
        )

        # Public key text file
        write_text(out / f"{name}_public.txt", f"PublicKey = {client_keys.public}\n")

        # Update keys.json
        keys_path = out / "keys.json"
        if keys_path.exists():
            keys_data: dict = json.loads(keys_path.read_text(encoding="utf-8"))
        else:
            keys_data = {"server": {"private": server_priv, "public": server_pub}, "peers": []}
        keys_data.setdefault("peers", []).append(
            {
                "name": name,
                "private": client_keys.private,
                "public": client_keys.public,
                "ip": client_vpn_ip,
            }
        )
        write_json(keys_path, keys_data)

        return {
            "output_dir": str(out),
            "server_pubkey": server_pub,
            "client_pubkey": client_keys.public,
        }
