"""WireGuard key generation — via pure Python (X25519), fallback wg.exe."""
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path
from typing import Optional

from models.keypair import KeyPair

WG_PATHS = [
    Path(r"C:\Program Files\WireGuard\wg.exe"),
    Path(r"C:\Program Files (x86)\WireGuard\wg.exe"),
]


class KeyGenError(RuntimeError):
    """Raised when key generation or wg.exe lookup fails."""


def find_wg() -> str:
    """Locate WireGuard binary — check standard paths then PATH."""
    candidates: list[Path | str] = (
        [*WG_PATHS, "wg.exe", "wg"] if sys.platform == "win32" else ["wg"]
    )
    for cmd in candidates:
        try:
            subprocess.run(
                [str(cmd), "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return str(cmd)
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            continue
    raise KeyGenError(
        "WireGuard not found. Please install WireGuard from "
        "https://www.wireguard.com/install/"
    )


def _wg_path() -> str:
    if not hasattr(_wg_path, "_cached"):
        _wg_path._cached = find_wg()
    return _wg_path._cached


def check_wg_available() -> Optional[str]:
    """Return error message if wg unavailable, or None."""
    try:
        _wg_path()
        return None
    except KeyGenError as exc:
        return str(exc)


def derive_pubkey(private_key: str) -> str:
    """Derive public key from private via Python X25519 or wg.exe fallback."""
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        priv_bytes = base64.b64decode(private_key)
        priv = X25519PrivateKey.from_private_bytes(priv_bytes)
        return base64.b64encode(priv.public_key().public_bytes_raw()).decode()
    except ImportError:
        wg = _wg_path()
        try:
            result = subprocess.run(
                [wg, "pubkey"],
                input=private_key.encode(),
                capture_output=True, check=True, timeout=10,
            )
            return result.stdout.decode().strip()
        except (subprocess.CalledProcessError, OSError) as exc:
            raise KeyGenError(f"Pubkey derivation failed: {exc}") from exc


def generate_keypair() -> KeyPair:
    """Generate a WireGuard key pair via Python X25519 or wg.exe fallback."""
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        priv = X25519PrivateKey.generate()
        return KeyPair(
            private=base64.b64encode(priv.private_bytes_raw()).decode(),
            public=base64.b64encode(priv.public_key().public_bytes_raw()).decode(),
        )
    except ImportError:
        wg = _wg_path()
        try:
            priv_b = subprocess.run(
                [wg, "genkey"], capture_output=True, check=True, timeout=10
            ).stdout.strip()
            pub = subprocess.run(
                [wg, "pubkey"], input=priv_b, capture_output=True, check=True, timeout=10,
            ).stdout.strip()
            return KeyPair(private=priv_b.decode(), public=pub.decode())
        except (subprocess.CalledProcessError, OSError) as exc:
            raise KeyGenError(f"Key generation failed: {exc}") from exc
