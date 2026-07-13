"""Client entry models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ClientStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class ClientEntry:
    """One VPN client within a project."""

    name: str
    vpn_ip: str
    private_key: str = ""
    public_key: str = ""
    status: ClientStatus = ClientStatus.ACTIVE
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    allowed_ips: str = ""  # per-client override, empty = use project subnet
    remote_type: str = ""
    remote_id: str = ""
    remote_password: str = ""

    def revoke(self) -> None:
        self.status = ClientStatus.REVOKED
