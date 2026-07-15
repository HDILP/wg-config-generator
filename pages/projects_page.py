"""Projects page — project list management for Client Mode."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from widgets import Card, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from app.app import GPServerManager


class ProjectsPage(ctk.CTkFrame):
    """Project management: list, open, create projects."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="项目列表",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        proj = ProjectManager.list_projects()

        if not proj:
            ctk.CTkLabel(self, text="暂无项目",
                         font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=20)
            PrimaryButton(
                self, text="新建项目", font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#2b7a4b", command=self._app.show_new_project,
            ).pack()
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        for name in reversed(proj):
            card = Card(scroll, corner_radius=8)
            card.pack(fill="x", pady=4)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=10)

            ctk.CTkLabel(row, text=f"📁  {name}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w").pack(side="left", fill="x", expand=True)

            SecondaryButton(
                row, text="打开", width=70, height=28,
                font=ctk.CTkFont(size=12),
                fg_color="#6750A4",
                text_color="#FFFFFF",
                command=lambda n=name: self._app.open_project_from_list(n),
            ).pack(side="right")

        PrimaryButton(
            self, text="➕ 新建项目",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b7a4b",
            command=self._app.show_new_project,
        ).pack(anchor="w", padx=24, pady=(0, 8))
