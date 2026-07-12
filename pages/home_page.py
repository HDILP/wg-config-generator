"""Home page — GP Server Manager landing."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import customtkinter as ctk

from core.project_manager import ProjectManager
from utils.file_ops import read_json

if TYPE_CHECKING:
    from app.app import GPServerManager


class HomePage(ctk.CTkFrame):
    """Landing page: New / Open / Settings / Recent projects."""

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        # Header
        ctk.CTkLabel(
            self, text="GP Server Manager",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(pady=(60, 4))
        ctk.CTkLabel(
            self, text="服务器生命周期管理工具",
            font=ctk.CTkFont(size=14),
            text_color="#79747E",
        ).pack(pady=(0, 40))

        # Action buttons
        btn_kw = dict(
            height=56, corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
        )

        ctk.CTkButton(
            self, text="📁  新建服务器",
            fg_color="#2b7a4b", hover_color="#1e5f38",
            command=self._app.show_new_project,
            **btn_kw,
        ).pack(fill="x", padx=60, pady=(0, 12))

        ctk.CTkButton(
            self, text="📂  打开服务器",
            fg_color="#6750A4", hover_color="#7C6DB5",
            command=self._app.show_project_list,
            **btn_kw,
        ).pack(fill="x", padx=60, pady=(0, 12))

        ctk.CTkButton(
            self, text="⚙  设置",
            fg_color="gray50", hover_color="gray40",
            command=self._app.show_settings,
            **btn_kw,
        ).pack(fill="x", padx=60, pady=(0, 40))

        # Recent projects
        recent = ProjectManager.list_projects()[-5:]  # last 5
        if recent:
            ctk.CTkLabel(
                self, text="最近打开",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#79747E",
            ).pack(anchor="w", padx=60, pady=(0, 8))

            for name in reversed(recent):
                row = ctk.CTkFrame(self, fg_color="transparent")
                row.pack(fill="x", padx=80, pady=2)
                ctk.CTkLabel(
                    row, text=f"•  {name}",
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                ).pack(side="left")
                ctk.CTkButton(
                    row, text="打开", width=60, height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color="transparent",
                    text_color="#6750A4",
                    hover_color="#F3EDF7",
                    command=lambda n=name: self._app.open_project(n),
                ).pack(side="right")
