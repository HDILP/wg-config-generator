"""Pure Python X25519 (Curve25519) key exchange — zero dependencies.

WireGuard private key = 32 random bytes (clamped).
Public key = X25519(private, basepoint).
Both base64-encoded for WireGuard format.

Reference: RFC 7748
"""
from __future__ import annotations

import base64
import os

P = 2**255 - 19
BASE = 9


def _mod(a: int) -> int:
    return a % P


def _mul(k: bytes, u: int = BASE) -> bytes:
    """X25519 function: scalar multiplication."""
    k = bytearray(k)
    k[0] &= 248
    k[31] = (k[31] & 127) | 64
    k = bytes(k)

    x1, x2, z2, x3, z3 = u, 1, 0, u, 1
    for i in range(255, -1, -1):
        bit = (k[i // 8] >> (i % 8)) & 1
        if bit:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        # A = x2 + z2
        a = _mod(x2 + z2)
        # AA = A^2
        aa = _mod(a * a)
        # B = x2 - z2
        b = _mod(x2 - z2)
        # BB = B^2
        bb = _mod(b * b)
        # E = AA - BB
        e = _mod(aa - bb)
        # C = x3 + z3
        c = _mod(x3 + z3)
        # D = x3 - z3
        d = _mod(x3 - z3)
        # DA = D * A
        da = _mod(d * a)
        # CB = C * B
        cb = _mod(c * b)
        # x3 = (DA + CB)^2
        x3 = _mod((da + cb) * (da + cb))
        # z3 = x1 * (DA - CB)^2
        z3 = _mod(_mod(x1 * (da - cb)) * (da - cb))
        # x2 = AA * BB
        x2 = _mod(aa * bb)
        # z2 = E * (AA + a24 * E)
        z2 = _mod(e * _mod(aa + 121665 * e))

    return _mod(x2 * pow(z2, P - 2, P)).to_bytes(32, "little")


def genkey() -> bytes:
    """Generate a random X25519 private key (32 bytes, clamped)."""
    return os.urandom(32)


def pubkey(private_key: bytes) -> bytes:
    """Derive X25519 public key from private key."""
    return _mul(private_key)


def genkey_b64() -> str:
    return base64.b64encode(genkey()).decode()


def pubkey_b64(private_b64: str) -> str:
    return base64.b64encode(pubkey(base64.b64decode(private_b64))).decode()
