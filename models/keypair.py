"""WireGuard key pair model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KeyPair:
    """A WireGuard key pair (private + public)."""
    private: str = ""
    public: str = ""
