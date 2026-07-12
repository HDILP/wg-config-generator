"""Client Dashboard — project overview for Client Mode."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from widgets import CardFrame

if TYPE_CHECKING:
    from app.app import GPServerManager


class ClientDashboardPage(ctk.CTkFrame):
    """Client mode dashboard: project stats, recent activity."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Client Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 8))

        proj = ProjectManager.list_projects()
        total_clients = sum(
            len(ProjectManager.load(n).clients) for n in proj[-50:]
        )

        # Stat cards row
        stat_frame = ctk.CTkFrame(self, fg_color="transparent")
        stat_frame.pack(fill="x", padx=24, pady=(0, 16))

        stats = [
            ("📁 项目", len(proj)),
            ("👥 客户端", total_clients),
            ("🖥 服务器", len(proj)),
        ]
        for label, val in stats:
            card = ctk.CTkFrame(stat_frame, corner_radius=12, width=160, height=80)
            card.pack(side="left", padx=(0, 12))
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=str(val),
                         font=ctk.CTkFont(size=28, weight="bold"),
                         ).pack(pady=(16, 2))
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12),
                         text_color="#79747E").pack()

        # Project list
        card = CardFrame(self, title="最近项目")
        card.pack(fill="x", padx=24, pady=(0, 12))

        if not proj:
            ctk.CTkLabel(card, text="暂无项目，请先在项目列表新建",
                         font=ctk.CTkFont(size=12),
                         text_color="#79747E").pack(pady=20)
        else:
            for name in reversed(proj[-8:]):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=2)
                ctk.CTkLabel(row, text=f"•  {name}",
                             font=ctk.CTkFont(size=13),
                             anchor="w").pack(side="left", fill="x", expand=True)
                ctk.CTkButton(
                    row, text="打开", width=60, height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color="transparent", text_color="#6750A4",
                    hover_color="#F3EDF7",
                    command=lambda n=name: self._app.open_project(n),
                ).pack(side="right")

        ctk.CTkButton(
            self, text="➕ 新建项目",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b7a4b",
            command=self._app.show_new_project,
        ).pack(anchor="w", padx=24)
