"""WorkspaceMode enum — no GUI imports, safe for models layer."""
from __future__ import annotations

from enum import Enum


class WorkspaceMode(str, Enum):
    SERVER = "server"
    CLIENT = "client"
    BOTH = "both"
