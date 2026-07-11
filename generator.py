"""Project manager — create, manage, and regenerate WireGuard projects."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from keygen import derive_pubkey, generate_keypair, KeyGenError
from models import ClientEntry, KeyPair, Project
from templates import CLIENT_CONF, PEER_BLOCK, README, SERVER_CONF
from utils import ensure_dir, write_json, write_text


class ProjectManager:
    """Stateless operations over projects/."""

    PROJECTS_DIR = Path("projects")

    # ── list ─────────────────────────────────────────────────

    @staticmethod
    def list_projects() -> List[str]:
        """Return sorted project names that have a project.json."""
        if not ProjectManager.PROJECTS_DIR.exists():
            return []
        out: List[str] = []
        for d in sorted(ProjectManager.PROJECTS_DIR.iterdir()):
            if d.is_dir() and (d / "project.json").exists():
                out.append(d.name)
        return out

    @staticmethod
    def load(name: str) -> Project:
        pj = ProjectManager.PROJECTS_DIR / name / "project.json"
        if not pj.exists():
            raise FileNotFoundError(f"project.json not found for '{name}'")
        return Project.load(pj)

    # ── create ───────────────────────────────────────────────

    @staticmethod
    def create(
        name: str,
        server_public_ip: str,
        listen_port: int = 51820,
        server_vpn_ip: str = "10.66.66.1",
        vpn_subnet: str = "10.66.66.0/24",
        remote_number: str = "",
    ) -> Project:
        """Generate server keys, create project dir, write everything."""
        if not name.strip():
            raise ValueError("Project name is required")
        keys = generate_keypair()
        project = Project(
            name=name.strip(),
            remote_number=remote_number.strip(),
            server_public_ip=server_public_ip.strip(),
            server_private_key=keys.private,
            server_public_key=keys.public,
            listen_port=listen_port,
            server_vpn_ip=server_vpn_ip.strip(),
            vpn_subnet=vpn_subnet.strip(),
        )
        _write_project(project)
        return project

    # ── add client ───────────────────────────────────────────

    @staticmethod
    def add_client(
        project: Project,
        client_name: str,
        vpn_ip: Optional[str] = None,
    ) -> ClientEntry:
        """Generate client keys, append, regenerate all configs."""
        if not client_name.strip():
            raise ValueError("Client name is required")
        if any(c.name == client_name.strip() for c in project.clients):
            raise ValueError(f"Client '{client_name}' already exists")

        used = {c.vpn_ip for c in project.clients} | {project.server_vpn_ip}
        if vpn_ip:
            if vpn_ip in used:
                raise ValueError(f"IP {vpn_ip} already in use")
        else:
            base = ".".join(project.server_vpn_ip.split(".")[:3])
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

    # ── remove client ────────────────────────────────────────

    @staticmethod
    def remove_client(project: Project, client_name: str) -> None:
        """Delete client entry, clean up files, regenerate server.conf."""
        project.clients = [c for c in project.clients if c.name != client_name]
        client_dir = project.dir / "clients" / client_name
        if client_dir.exists():
            shutil.rmtree(client_dir)
        _write_project(project)

    # ── regenerate all from project.json ─────────────────────

    @staticmethod
    def regenerate(project: Project) -> None:
        """Rewrite server.conf + all client confs from project.json data."""
        _write_configs(project)


# ── internal helpers ─────────────────────────────────────────


def _next_ip(used: set[str], base: str) -> str:
    """Return first un-used .2–.254 in base subnet."""
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
    """Generate server.conf + every client.conf from project data."""
    _write_server_conf(project)
    _write_readme(project)
    write_text(project.dir / "server_public.txt",
               f"PublicKey = {project.server_public_key}\n")
    for client in project.clients:
        _write_client_conf(project, client)


def _write_server_conf(project: Project) -> None:
    peers = "\n\n".join(
        PEER_BLOCK.format(public_key=c.public_key, allowed_ips=f"{c.vpn_ip}/32")
        for c in project.clients
    )
    write_text(
        project.dir / "server.conf",
        SERVER_CONF.format(
            private_key=project.server_private_key,
            address=f"{project.server_vpn_ip}/24",
            listen_port=project.listen_port,
            peers_section=peers,
        ),
    )


def _write_client_conf(project: Project, client: ClientEntry) -> None:
    out_dir = ensure_dir(project.clients_dir / client.name)
    write_text(
        out_dir / "client.conf",
        CLIENT_CONF.format(
            private_key=client.private_key,
            address=f"{client.vpn_ip}/24",
            server_public_key=project.server_public_key,
            endpoint=f"{project.server_public_ip}:{project.listen_port}",
            allowed_ips=project.vpn_subnet,
            persistent_keepalive=25,
        ),
    )


def _write_readme(project: Project) -> None:
    write_text(
        project.dir / "README.txt",
        README.format(
            server_public_ip=project.server_public_ip,
            server_vpn_ip=project.server_vpn_ip,
            client_vpn_ip="(see per-client configs)",
            listen_port=project.listen_port,
        ),
    )
