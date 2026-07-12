"""Customers page — client overview across all projects (Client Mode)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager

if TYPE_CHECKING:
    from app.app import GPServerManager


class CustomersPage(ctk.CTkFrame):
    """View all clients across projects."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="客户管理",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        proj = ProjectManager.list_projects()

        if not proj:
            ctk.CTkLabel(self, text="暂无项目",
                         font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        for pname in reversed(proj):
            try:
                project = ProjectManager.load(pname)
            except Exception:
                continue

            # Project header
            ctk.CTkLabel(scroll, text=f"📁  {pname}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#6750A4",
                         ).pack(anchor="w", pady=(12, 4))

            if not project.clients:
                ctk.CTkLabel(scroll, text="  暂无客户端",
                             font=ctk.CTkFont(size=12),
                             text_color="#79747E",
                             ).pack(anchor="w", padx="16")
            else:
                for c in project.clients:
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", padx=16, pady=2)
                    ctk.CTkLabel(row, text=f"  👤  {c.name}",
                                 font=ctk.CTkFont(size=13),
                                 width=160, anchor="w").pack(side="left")
                    ctk.CTkLabel(row, text=c.vpn_ip,
                                 font=ctk.CTkFont(size=12),
                                 text_color="#79747E",
                                 width=120).pack(side="left")
                    ctk.CTkLabel(row, text=c.status.value,
                                 font=ctk.CTkFont(size=11),
                                 text_color="#4CAF50" if c.status.value == "active" else "#9E9E9E",
                                 ).pack(side="left")
