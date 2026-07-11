"""Data models for WireGuard Project Manager."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class KeyPair:
    """A WireGuard key pair (private + public)."""
    private: str = ""
    public: str = ""


@dataclass
class ClientEntry:
    """One client within a project."""

    name: str
    vpn_ip: str
    private_key: str = ""
    public_key: str = ""


@dataclass
class Project:
    """A complete WireGuard server project — single source of truth."""

    name: str
    server_public_ip: str
    remote_number: str = ""  # 帮我吧 / 向日葵 远程协助号码
    server_private_key: str = ""
    server_public_key: str = ""
    listen_port: int = 51820
    server_vpn_ip: str = "10.66.66.1"
    vpn_subnet: str = "10.66.66.0/24"
    clients: List[ClientEntry] = field(default_factory=list)

    # ── disk layout ──────────────────────────────────────────

    @property
    def dir(self) -> Path:
        return Path("projects") / self.name

    @property
    def clients_dir(self) -> Path:
        return self.dir / "clients"

    # ── serialization ────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "remote_number": self.remote_number,
            "server": {
                "public_ip": self.server_public_ip,
                "private_key": self.server_private_key,
                "public_key": self.server_public_key,
                "vpn_ip": self.server_vpn_ip,
                "listen_port": self.listen_port,
            },
            "vpn_subnet": self.vpn_subnet,
            "clients": [
                {
                    "name": c.name,
                    "vpn_ip": c.vpn_ip,
                    "private_key": c.private_key,
                    "public_key": c.public_key,
                }
                for c in self.clients
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Project:
        srv = data["server"]
        return cls(
            name=data["name"],
            server_public_ip=srv["public_ip"],
            server_private_key=srv["private_key"],
            server_public_key=srv["public_key"],
            listen_port=srv.get("listen_port", 51820),
            server_vpn_ip=srv.get("vpn_ip", "10.66.66.1"),
            vpn_subnet=data.get("vpn_subnet", "10.66.66.0/24"),
            clients=[ClientEntry(**c) for c in data.get("clients", [])],
        )

    @classmethod
    def load(cls, path: Path) -> Project:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_json(self) -> None:
        from utils import write_json
        write_json(self.dir / "project.json", self.to_dict())
