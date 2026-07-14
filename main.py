#!/usr/bin/env python3
"""GP Server Manager — Enterprise server lifecycle management tool.

Entry point. Shows workspace mode selector at startup, then launches the app.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)

from models.app_settings import AppSettings
from app.workspace import WorkspaceMode


def main() -> None:
    settings = AppSettings.load()

    # Determine workspace mode
    workspace = _resolve_workspace(settings)

    # Apply theme from settings
    from app.theme import apply_theme, ThemeMode
    theme_map = {"light": ThemeMode.LIGHT, "dark": ThemeMode.DARK, "system": ThemeMode.SYSTEM}
    apply_theme(theme_map.get(settings.theme, ThemeMode.LIGHT))

    # Ensure Projects dir exists
    from core.project_manager import ProjectManager
    ProjectManager.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Launch app
    from app import GPServerManager
    app = GPServerManager(workspace=workspace, settings=settings)
    app.mainloop()


def _resolve_workspace(settings: AppSettings) -> WorkspaceMode:
    """Show launcher dialog or auto-select based on saved settings."""
    if settings.remember_workspace and settings.workspace_mode in ("server", "client"):
        return WorkspaceMode(settings.workspace_mode)

    if settings.workspace_mode == "server":
        return WorkspaceMode.SERVER
    elif settings.workspace_mode == "client":
        return WorkspaceMode.CLIENT

    # Show launcher dialog
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()

    from app.launcher import WorkspaceLauncher
    dlg = WorkspaceLauncher(root, remember=settings.remember_workspace)
    root.wait_window(dlg)

    mode, remember = dlg.result()
    root.destroy()

    if mode is None:
        sys.exit(0)

    # Save if "remember my choice" is checked
    if remember:
        settings.workspace_mode = mode.value
        settings.remember_workspace = True
        settings.save()

    return mode


if __name__ == "__main__":
    main()
