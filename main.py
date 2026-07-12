#!/usr/bin/env python3
"""GP Server Manager — Enterprise server lifecycle management tool.

Entry point. Run this file to start the GUI application.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # Ensure Projects dir exists at startup
    from core.project_manager import ProjectManager
    ProjectManager.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Launch app
    from app import GPServerManager
    app = GPServerManager()
    app.mainloop()


if __name__ == "__main__":
    main()
