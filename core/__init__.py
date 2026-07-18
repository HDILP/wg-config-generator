"""Core — key generation, templates, project management."""
from core.project_manager import ProjectManager
from core.qrcode_gen import client_conf_to_qr
from core.templates import CLIENT_CONF, CLIENT_README, PEER_BLOCK, README, SERVER_CONF
from core.wg_keygen import (
    KeyGenError,
    check_wg_available,
    derive_pubkey,
    find_wg,
    generate_keypair,
)

__all__ = [
    "ProjectManager",
    "client_conf_to_qr",
    "SERVER_CONF",
    "CLIENT_CONF",
    "PEER_BLOCK",
    "README",
    "CLIENT_README",
    "generate_keypair",
    "derive_pubkey",
    "check_wg_available",
    "find_wg",
    "KeyGenError",
]
