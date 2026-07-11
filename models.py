"""Data models for WireGuard configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class KeyPair:
    """A WireGuard key pair (private + public)."""

    private: str = ""
    public: str = ""


@dataclass
class PeerConfig:
    """A single [Peer] section attached to a server."""

    public_key: str
    allowed_ips: str  # e.g. "10.66.66.2/32"


@dataclass
class ServerConfig:
    """Server-side WireGuard config."""

    private_key: str
    address: str  # e.g. "10.66.66.1/24"
    listen_port: int = 51820
    peers: List[PeerConfig] = field(default_factory=list)


@dataclass
class ClientConfig:
    """Client-side WireGuard config (single peer)."""

    private_key: str
    address: str  # e.g. "10.66.66.2/24"
    server_public_key: str
    endpoint: str  # e.g. "1.2.3.4:51820"
    allowed_ips: str = "10.66.66.0/24"
    persistent_keepalive: int = 25


@dataclass
class GenerationConfig:
    """User-facing settings for one generation run."""

    server_public_ip: str
    listen_port: int = 51820
    server_vpn_ip: str = "10.66.66.1"
    client_vpn_ip: str = "10.66.66.2"
    vpn_subnet: str = "10.66.66.0/24"
    output_dir: str = "output"
