"""ProjectManager — create, manage, and regenerate server projects.

Single source of truth: project.json lives inside each Project directory.
All .conf files are auto-generated from project.json — never edit them manually.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from core.templates import CLIENT_CONF, CLIENT_README, PEER_BLOCK, README, SERVER_CONF
from core.wg_keygen import derive_pubkey, generate_keypair, KeyGenError
from models.client import ClientEntry, ClientStatus
from models.keypair import KeyPair
from models.project import OpsInfo, Project, ProjectSettings, RemoteInfo, SqlConfig
from utils.file_ops import ensure_dir, write_json, write_text


class ProjectManager:
    """Stateless operations over Projects/."""

    PROJECTS_DIR = Path("Projects")

    # ── list / load ───────────────────────────────────────────────

    @staticmethod
    def list_projects() -> List[str]:
        """Return sorted project names that have a project.json."""
        if not ProjectManager.PROJECTS_DIR.exists():
            return []
        out: List[str] = []
        for d in sorted(ProjectManager.PROJECTS_DIR.iterdir()):
            if (d.is_dir() and d.name != "__local_server__"
                    and (d / "project.json").exists()):
                out.append(d.name)
        return out

    @staticmethod
    def load(name: str) -> Project:
        pj = ProjectManager.PROJECTS_DIR / name / "project.json"
        if not pj.exists():
            raise FileNotFoundError(f"Project '{name}' not found")
        return Project.load(pj)

    # ── create ────────────────────────────────────────────────────

    @staticmethod
    def create(
        name: str,
        public_ip: str = "",
        listen_port: int = 51820,
        vpn_ip: str = "10.66.66.1",
        subnet: str = "10.66.66.0/24",
        remote_type: str = "Sunlogin",
        remote_id: str = "",
        remote_password: str = "",
    ) -> Project:
        if not name.strip():
            raise ValueError("Project name is required")
        if (ProjectManager.PROJECTS_DIR / name.strip()).exists():
            raise ValueError(f"Project '{name.strip()}' already exists")

        keys = generate_keypair()
        settings = ProjectSettings(
            name=name.strip(),
            public_ip=public_ip.strip(),
            listen_port=listen_port,
            vpn_ip=vpn_ip.strip(),
            subnet=subnet.strip(),
            remote=RemoteInfo(type=remote_type, id=remote_id.strip()),
            sql=SqlConfig(),
            ops=OpsInfo(remote_type=remote_type, remote_id=remote_id.strip(),
                        password=remote_password.strip()),
        )
        project = Project(
            settings=settings,
            server_keypair=keys,
        )
        _write_project(project)
        return project

    # ── add client ────────────────────────────────────────────────

    @staticmethod
    def add_client(
        project: Project,
        client_name: str,
        vpn_ip: Optional[str] = None,
    ) -> ClientEntry:
        if not client_name.strip():
            raise ValueError("Client name is required")
        if any(c.name == client_name.strip() for c in project.clients):
            raise ValueError(f"Client '{client_name}' already exists")

        used = {c.vpn_ip for c in project.clients} | {project.settings.vpn_ip}
        if vpn_ip:
            if vpn_ip in used:
                raise ValueError(f"IP {vpn_ip} already in use")
        else:
            base = ".".join(project.settings.vpn_ip.split(".")[:3])
            vpn_ip = _next_ip(used, base)

        keys = generate_keypair()
        entry = ClientEntry(
            name=client_name.strip(),
            vpn_ip=vpn_ip,
            private_key=keys.private,
            public_key=keys.public,
        )
        project.clients.append(entry)
        _write_project(project)
        return entry

    # ── save / regenerate ────────────────────────────────────────

    @staticmethod
    def save(project: Project) -> None:
        _write_project(project)

    @staticmethod
    def regenerate(project: Project) -> None:
        _write_configs(project)

    @staticmethod
    def regenerate_client(project: Project, client_name: str) -> ClientEntry:
        """Regenerate keys for one client, update everything."""
        for c in project.clients:
            if c.name == client_name:
                keys = generate_keypair()
                c.private_key = keys.private
                c.public_key = keys.public
                _write_project(project)
                return c
        raise ValueError(f"Client '{client_name}' not found")

    # ── remove / revoke client ────────────────────────────────────

    @staticmethod
    def remove_client(project: Project, client_name: str) -> None:
        project.clients = [c for c in project.clients if c.name != client_name]
        client_dir = project.dir / "clients" / client_name
        if client_dir.exists():
            shutil.rmtree(client_dir)
        _write_project(project)

    @staticmethod
    def revoke_client(project: Project, client_name: str) -> None:
        for c in project.clients:
            if c.name == client_name:
                c.status = ClientStatus.REVOKED
                _write_project(project)
                return
        raise ValueError(f"Client '{client_name}' not found")

    # ── export ────────────────────────────────────────────────────

    @staticmethod
    def export_client_config(project: Project, client_name: str) -> str:
        """Return the client.conf text for a given client."""
        for c in project.clients:
            if c.name == client_name:
                return CLIENT_CONF.format(
                    private_key=c.private_key,
                    address=f"{c.vpn_ip}/24",
                    dns="1.1.1.1",
                    server_public_key=project.server_keypair.public,
                    endpoint=f"{project.settings.public_ip}:{project.settings.listen_port}",
                    allowed_ips=project.settings.subnet,
                    persistent_keepalive=25,
                )
        raise ValueError(f"Client '{client_name}' not found")

    @staticmethod
    def export_server_conf(project: Project) -> str:
        peers = "\n\n".join(
            PEER_BLOCK.format(
                client_name=c.name,
                public_key=c.public_key,
                allowed_ips=f"{c.vpn_ip}/32",
            )
            for c in project.clients
            if c.status == ClientStatus.ACTIVE
        )
        return SERVER_CONF.format(
            private_key=project.server_keypair.private,
            address=f"{project.settings.vpn_ip}/24",
            listen_port=project.settings.listen_port,
            peers_section=peers,
        )


# ── internal helpers ─────────────────────────────────────────────


def _next_ip(used: set[str], base: str) -> str:
    # ponytail: linear scan, fine for <253 clients
    for i in range(2, 255):
        ip = f"{base}.{i}"
        if ip not in used:
            return ip
    raise RuntimeError(f"No available IPs in {base}.0/24")


def _write_project(project: Project) -> None:
    """Full write: project.json + all config files."""
    d = ensure_dir(project.dir)
    ensure_dir(project.clients_dir)
    write_json(d / "project.json", project.to_dict())
    _write_configs(project)


def _write_configs(project: Project) -> None:
    """Generate server.conf + all client files from project data."""
    _write_server_conf(project)
    _write_readme(project)
    write_text(
        project.dir / "server_public.txt",
        f"PublicKey = {project.server_keypair.public}\n",
    )
    for client in project.clients:
        _write_client_full(project, client)


def _write_server_conf(project: Project) -> None:
    s = project.settings
    active = [c for c in project.clients if c.status == ClientStatus.ACTIVE]
    peers = "\n\n".join(
        PEER_BLOCK.format(
            client_name=c.name,
            public_key=c.public_key,
            allowed_ips=f"{c.vpn_ip}/32",
        )
        for c in active
    )
    write_text(
        project.dir / "server.conf",
        SERVER_CONF.format(
            private_key=project.server_keypair.private,
            address=f"{s.vpn_ip}/24",
            listen_port=s.listen_port,
            peers_section=peers,
        ),
    )


def _write_client_full(project: Project, client: ClientEntry) -> None:
    s = project.settings
    out_dir = ensure_dir(project.clients_dir / client.name)
    cfg = CLIENT_CONF.format(
        private_key=client.private_key,
        address=f"{client.vpn_ip}/24",
        dns="1.1.1.1",
        server_public_key=project.server_keypair.public,
        endpoint=f"{s.public_ip}:{s.listen_port}",
        allowed_ips=s.subnet,
        persistent_keepalive=25,
    )
    write_text(out_dir / "client.conf", cfg)

    write_text(
        out_dir / "README.txt",
        CLIENT_README.format(
            client_name=client.name,
            vpn_ip=client.vpn_ip,
            server_public_ip=s.public_ip,
            listen_port=s.listen_port,
        ),
    )

    import json
    write_json(
        out_dir / "keys.json",
        {
            "name": client.name,
            "vpn_ip": client.vpn_ip,
            "private_key": client.private_key,
            "public_key": client.public_key,
            "status": client.status.value,
        },
    )

    # QR code (optional dep)
    try:
        from core.qrcode_gen import generate_qr_code

        generate_qr_code(cfg, out_dir / "qrcode.png")
    except ImportError:
        pass


def _write_readme(project: Project) -> None:
    s = project.settings
    write_text(
        project.dir / "README.txt",
        README.format(
            server_name=s.name,
            server_public_ip=s.public_ip,
            server_vpn_ip=s.vpn_ip,
            client_vpn_ip="(see per-client configs)",
            listen_port=s.listen_port,
            remote_type=s.ops.remote_type or s.remote.type,
            remote_id=s.ops.remote_id or s.remote.id,
            contact=s.ops.contact,
        ),
    )
