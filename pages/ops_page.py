"""Ops info page — editable operational information for a project."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.project import Project

if TYPE_CHECKING:
    from app.app import GPServerManager


class OpsInfoPage(ctk.CTkFrame):
    """Operational information editor."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, project: Project, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._entries: Dict[str, ctk.CTkEntry] = {}
        self._build()

    def _build(self) -> None:
        o = self._project.settings.ops

        ctk.CTkLabel(self, text="运维信息", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="x", padx=24, pady=(0, 12))

        fields = [
            ("远程软件", "remote_type", o.remote_type, ["帮我吧", "向日葵", "ToDesk", "RustDesk", "Other"]),
            ("远程号码", "remote_id", o.remote_id, None),
            ("负责人", "contact", o.contact, None),
            ("密码", "password", o.password, None),
            ("备注", "note", o.note, None),
            ("服务器地区", "region", o.region, None),
            ("SQL 版本", "sql_version", o.sql_version, None),
            ("管家婆版本", "gp_version", o.gp_version, None),
        ]

        for label, key, default, options in fields:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)

            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13),
                         width=80, anchor="w").pack(side="left")

            if options:
                var = ctk.StringVar(value=default)
                self._entries[key] = ctk.CTkOptionMenu(
                    row, values=options, variable=var,
                    font=ctk.CTkFont(size=12),
                )
            else:
                entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=13))
                entry.insert(0, default or "")
                if key == "password":
                    entry.configure(show="*")
                self._entries[key] = entry

            self._entries[key].pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Actions
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkButton(act, text="← 返回仪表盘", width=110,
                       font=ctk.CTkFont(size=12),
                       command=lambda: self._app.show_dashboard(),
                       ).pack(side="left")

        ctk.CTkButton(act, text="💾 保存", font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color="#2b7a4b",
                       command=self._save,
                       ).pack(side="right")

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(8, 4))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _save(self) -> None:
        o = self._project.settings.ops
        o.remote_type = self._entries["remote_type"].get()
        o.remote_id = self._entries["remote_id"].get()
        o.contact = self._entries["contact"].get()
        o.password = self._entries["password"].get()
        o.note = self._entries["note"].get()
        o.region = self._entries["region"].get()
        o.sql_version = self._entries["sql_version"].get()
        o.gp_version = self._entries["gp_version"].get()

        # Sync remote info to project-level remote
        self._project.settings.remote.type = o.remote_type
        self._project.settings.remote.id = o.remote_id

        ProjectManager.save(self._project)
        self._set_status("✓ 运维信息已保存")
