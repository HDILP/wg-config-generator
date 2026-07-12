"""Project model — a Project = one server."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from models.backup import BackupPolicy
from models.client import ClientEntry
from models.keypair import KeyPair


@dataclass
class RemoteInfo:
    """Remote access software info."""
    type: str = "Sunlogin"  # Sunlogin / ToDesk / RustDesk / Aishu / Other
    id: str = ""


@dataclass
class SqlConfig:
    """SQL Server config for this server instance."""
    instance: str = "MSSQLSERVER"
    port: int = 65529
    listen: str = "127.0.0.1"  # 127.0.0.1 or 0.0.0.0


@dataclass
class OpsInfo:
    """Operational info stored in project, all editable."""
    remote_type: str = "Sunlogin"
    remote_id: str = ""
    contact: str = ""
    password: str = ""
    note: str = ""
    region: str = ""
    sql_version: str = ""
    gp_version: str = ""


@dataclass
class ProjectSettings:
    """Mutable project settings — persisted in project.json."""
    name: str
    public_ip: str = ""
    listen_port: int = 51820
    vpn_ip: str = "10.66.66.1"
    subnet: str = "10.66.66.0/24"

    remote: RemoteInfo = field(default_factory=RemoteInfo)

    sql: SqlConfig = field(default_factory=SqlConfig)

    ops: OpsInfo = field(default_factory=OpsInfo)

    backup: BackupPolicy = field(default_factory=BackupPolicy)

    note: str = ""


@dataclass
class Project:
    """A complete server project — single source of truth.

    A Project = one server. Everything lives under projects/<name>/.
    """

    settings: ProjectSettings
    server_keypair: KeyPair = field(default_factory=KeyPair)
    clients: List[ClientEntry] = field(default_factory=list)

    # ── disk layout ──────────────────────────────────────────

    PROJECTS_DIR: Path = Path("Projects")

    @property
    def dir(self) -> Path:
        return self.PROJECTS_DIR / self.settings.name

    @property
    def clients_dir(self) -> Path:
        return self.dir / "clients"

    # ── convenience props ────────────────────────────────────

    @property
    def name(self) -> str:
        return self.settings.name

    # ── serialization ────────────────────────────────────────

    def to_dict(self) -> Dict:
        s = self.settings
        ops = s.ops
        return {
            "name": s.name,
            "public_ip": s.public_ip,
            "listen_port": s.listen_port,
            "vpn_ip": s.vpn_ip,
            "subnet": s.subnet,
            "server_private_key": self.server_keypair.private,
            "server_public_key": self.server_keypair.public,
            "remote": {
                "type": s.remote.type,
                "id": s.remote.id,
            },
            "sql": {
                "instance": s.sql.instance,
                "port": s.sql.port,
                "listen": s.sql.listen,
            },
            "ops": {
                "remote_type": ops.remote_type,
                "remote_id": ops.remote_id,
                "contact": ops.contact,
                "password": ops.password,
                "note": ops.note,
                "region": ops.region,
                "sql_version": ops.sql_version,
                "gp_version": ops.gp_version,
            },
            "backup": {
                "enabled": s.backup.enabled,
                "databases": s.backup.databases,
                "schedule_time": s.backup.schedule_time,
                "save_path": s.backup.save_path,
                "retention_days": s.backup.retention_days,
                "compression": s.backup.compression,
                "compression_auto_disabled": s.backup.compression_auto_disabled,
            },
            "note": s.note,
            "clients": [
                {
                    "name": c.name,
                    "vpn_ip": c.vpn_ip,
                    "private_key": c.private_key,
                    "public_key": c.public_key,
                    "status": c.status.value,
                    "note": c.note,
                    "created_at": c.created_at,
                    "allowed_ips": c.allowed_ips,
                }
                for c in self.clients
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Project:
        ops_data = data.get("ops", {})
        remote_data = data.get("remote", {})
        sql_data = data.get("sql", {})
        settings = ProjectSettings(
            name=data["name"],
            public_ip=data.get("public_ip", ""),
            listen_port=data.get("listen_port", 51820),
            vpn_ip=data.get("vpn_ip", "10.66.66.1"),
            subnet=data.get("subnet", "10.66.66.0/24"),
            remote=RemoteInfo(
                type=remote_data.get("type", "Sunlogin"),
                id=remote_data.get("id", ""),
            ),
            sql=SqlConfig(
                instance=sql_data.get("instance", "MSSQLSERVER"),
                port=sql_data.get("port", 65529),
                listen=sql_data.get("listen", "127.0.0.1"),
            ),
            ops=OpsInfo(
                remote_type=ops_data.get("remote_type", ""),
                remote_id=ops_data.get("remote_id", ""),
                contact=ops_data.get("contact", ""),
                password=ops_data.get("password", ""),
                note=ops_data.get("note", ""),
                region=ops_data.get("region", ""),
                sql_version=ops_data.get("sql_version", ""),
                gp_version=ops_data.get("gp_version", ""),
            ),
            note=data.get("note", ""),
            backup=BackupPolicy(
                enabled=bd.get("enabled", False),
                databases=bd.get("databases", []),
                schedule_time=bd.get("schedule_time", "02:00"),
                save_path=bd.get("save_path", "D:\\SQLBackup"),
                retention_days=bd.get("retention_days", 30),
                compression=bd.get("compression", True),
                compression_auto_disabled=bd.get("compression_auto_disabled", False),
            ) if (bd := data.get("backup")) else BackupPolicy(),
        )
        clients = []
        for c in data.get("clients", []):
            from models.client import ClientStatus
            status_str = c.get("status", "active")
            try:
                status = ClientStatus(status_str)
            except ValueError:
                status = ClientStatus.ACTIVE
            clients.append(ClientEntry(
                name=c["name"],
                vpn_ip=c["vpn_ip"],
                private_key=c.get("private_key", ""),
                public_key=c.get("public_key", ""),
                status=status,
                note=c.get("note", ""),
                created_at=c.get("created_at", ""),
                allowed_ips=c.get("allowed_ips", ""),
            ))
        return cls(
            settings=settings,
            server_keypair=KeyPair(
                private=data.get("server_private_key", ""),
                public=data.get("server_public_key", ""),
            ),
            clients=clients,
        )

    @classmethod
    def load(cls, path: Path) -> Project:
        """Load project from a project.json path."""
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_json(self) -> None:
        """Write project.json to disk."""
        from utils.file_ops import write_json
        write_json(self.dir / "project.json", self.to_dict())
