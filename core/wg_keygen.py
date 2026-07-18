"""WireGuard key generation — via pure Python X25519 (zero deps)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from core.x25519 import genkey_b64, pubkey_b64
from models.keypair import KeyPair


def generate_keypair() -> KeyPair:
    priv = genkey_b64()
    return KeyPair(private=priv, public=pubkey_b64(priv))


def derive_pubkey(private_key: str) -> str:
    return pubkey_b64(private_key)


def check_wg_available() -> Optional[str]:
    """Return error message if wg unavailable, or None."""
    try:
        _wg_path()
        return None
    except Exception as exc:
        return str(exc)


class KeyGenError(RuntimeError):
    """Raised when wg.exe fails."""


WG_PATHS = [
    Path(r"C:\Program Files\WireGuard\wg.exe"),
    Path(r"C:\Program Files (x86)\WireGuard\wg.exe"),
]


def find_wg() -> str:
    """Locate WireGuard binary — for `wg show` status display."""
    for cmd in [*WG_PATHS, "wg.exe", "wg"]:
        try:
            subprocess.run([str(cmd), "--version"], capture_output=True, check=True, timeout=5)
            return str(cmd)
        except Exception:
            continue
    raise KeyGenError("wg.exe not found (optional for keygen, needed for WireGuard status)")


def _wg_path() -> str:
    if not hasattr(_wg_path, "_cached"):
        for cmd in [*WG_PATHS, "wg.exe", "wg"]:
            try:
                subprocess.run([str(cmd), "--version"], capture_output=True, check=True, timeout=5)
                _wg_path._cached = str(cmd)
                break
            except Exception:
                continue
        else:
            raise KeyGenError("wg.exe not found")
    return _wg_path._cached
