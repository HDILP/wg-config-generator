"""WireGuard key generation via official wg executable."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from models import KeyPair


# Standard install paths for Windows — checked before PATH lookup.
WG_PATHS = [
    Path(r"C:\Program Files\WireGuard\wg.exe"),
    Path(r"C:\Program Files (x86)\WireGuard\wg.exe"),
]


class KeyGenError(RuntimeError):
    """Raised when key generation fails."""


def _find_wg() -> str:
    """Locate the WireGuard binary — checks default paths then PATH."""
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
        "WireGuard not found. Install WireGuard and ensure `wg` is on PATH."
    )


def _wg_binary() -> str:
    """Cached path to the wg binary."""
    if not hasattr(_wg_binary, "_cached"):
        _wg_binary._cached = _find_wg()  # type: ignore[attr-defined]
    return _wg_binary._cached  # type: ignore[attr-defined]


def check_wg_available() -> Optional[str]:
    """Return an error message if wg is unavailable, or None if OK."""
    try:
        _wg_binary()
        return None
    except KeyGenError as exc:
        return str(exc)


def derive_pubkey(private_key: str) -> str:
    """Derive public key from private key via `wg pubkey`."""
    wg = _wg_binary()
    try:
        result = subprocess.run(
            [wg, "pubkey"],
            input=private_key.encode(),
            capture_output=True,
            check=True,
            timeout=10,
        )
        return result.stdout.decode().strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise KeyGenError(f"Pubkey derivation failed: {exc}") from exc


def generate_keypair() -> KeyPair:
    """
    Generate a WireGuard key pair.
    
    Calls `wg genkey` then pipes the result to `wg pubkey`.
    """
    wg = _wg_binary()
    try:
        priv = subprocess.run(
            [wg, "genkey"],
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        pub = subprocess.run(
            [wg, "pubkey"],
            input=priv,
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        return KeyPair(private=priv.decode(), public=pub.decode())
    except (subprocess.CalledProcessError, OSError) as exc:
        raise KeyGenError(f"Key generation failed: {exc}") from exc
