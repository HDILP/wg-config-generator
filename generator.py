"""Config generation orchestrator — wires keygen, templates, and file output."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from keygen import generate_keypair, KeyGenError
from models import GenerationConfig, KeyPair, PeerConfig, ServerConfig, ClientConfig
from templates import SERVER_CONF, CLIENT_CONF, PEER_BLOCK, README
from utils import ensure_dir, write_text, write_json, open_folder


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

        # 8. JSON key store (for future management)
        write_json(
            out / "keys.json",
            {
                "server": {"private": server_keys.private, "public": server_keys.public},
                "client": {"private": client_keys.private, "public": client_keys.public},
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
