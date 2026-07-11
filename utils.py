"""Utility functions — file I/O, OS helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def ensure_dir(path: str | Path) -> Path:
    """Create directory if missing and return resolved Path."""
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text file."""
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write pretty-printed JSON."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def open_folder(path: Path) -> None:
    """Open directory in platform file manager."""
    cmd: list[str]
    if sys.platform == "win32":
        cmd = ["explorer", str(path.resolve())]
    elif sys.platform == "darwin":
        cmd = ["open", str(path.resolve())]
    else:
        cmd = ["xdg-open", str(path.resolve())]
    subprocess.Popen(cmd, start_new_session=True)
