"""GP Server Manager Application."""
from __future__ import annotations


def __getattr__(name):
    if name == "GPServerManager":
        from app.app import GPServerManager
        return GPServerManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GPServerManager"]
