"""Projects page — project list management for Client Mode."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.theme import C, PAD
from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from utils.icon_loader import load_icon
from widgets.empty_state import EmptyState

if TYPE_CHECKING:
    from app.app import GPServerManager


class ProjectsPage(ctk.CTkFrame):
    """Project management: list, open, create, delete projects."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="项目列表",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        proj = ProjectManager.list_projects()

        if not proj:
            EmptyState(
                self, icon="folder-open",
                text="还没有项目",
                subtext="新建第一个服务器项目",
                button_text="新建项目",
                on_click=self._app.show_new_project,
            ).pack(fill="both", expand=True)
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12,
                                                 fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        scroll.pack(fill="both", expand=True, padx=PAD["xl"], pady=(0, PAD["md"]))

        for name in reversed(proj):
            card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
            card.pack(fill="x", pady=3)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=PAD["md"])

            folder_icon = load_icon("folder-open", size=16, color=C["primary"])
            ctk.CTkLabel(row, text="", image=folder_icon).pack(side="left", padx=(0, PAD["sm"]))
            ctk.CTkLabel(
                row, text=name,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=C["on_surface"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkButton(
                row, text="打开", width=70, height=28,
                font=ctk.CTkFont(size=12),
                fg_color=C["primary"],
                text_color=C["on_primary"],
                corner_radius=8,
                command=lambda n=name: self._app.open_project_from_list(n),
            ).pack(side="right")

        ctk.CTkButton(
            self, text="➕ 新建项目",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["primary"],
            text_color=C["on_primary"],
            hover_color=C["primary_hover"],
            corner_radius=8,
            command=self._app.show_new_project,
        ).pack(anchor="w", padx=PAD["xl"], pady=(0, PAD["md"]))
