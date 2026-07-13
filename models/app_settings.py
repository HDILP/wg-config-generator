"""AppSettings — persistent global settings stored in settings.json."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.workspace import WorkspaceMode

SETTINGS_PATH = Path("settings.json")


@dataclass
class AppSettings:
    """Global application settings, persisted to settings.json."""

    workspace_mode: str = "ask"  # "server" | "client" | "ask"
    remember_workspace: bool = False
    theme: str = "light"  # "light" | "dark" | "system"
    language: str = "zh"
    projects_dir: str = "Projects"

    def effective_workspace(self) -> WorkspaceMode:
        if self.workspace_mode == "server":
            return WorkspaceMode.SERVER
        elif self.workspace_mode == "client":
            return WorkspaceMode.CLIENT
        return WorkspaceMode.SERVER  # fallback; "ask" means interactive

    def to_dict(self) -> dict:
        return {
            "workspace_mode": self.workspace_mode,
            "remember_workspace": self.remember_workspace,
            "theme": self.theme,
            "language": self.language,
            "projects_dir": self.projects_dir,
        }

    @classmethod
    def load(cls) -> AppSettings:
        path = Path(SETTINGS_PATH)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                workspace_mode=data.get("workspace_mode", "ask"),
                remember_workspace=data.get("remember_workspace", False),
                theme=data.get("theme", "light"),
                language=data.get("language", "zh"),
                projects_dir=data.get("projects_dir", "Projects"),
            )
        except (json.JSONDecodeError, KeyError):
            return cls()

    def save(self) -> None:
        Path(SETTINGS_PATH).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
