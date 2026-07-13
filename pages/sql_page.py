"""SQL Server page — view and configure SQL Server instance."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.workspace import WorkspaceMode
from models.project import Project
from services.sql_service import (
    SqlListenMode,
    get_sql_info,
    restart_sql,
    set_sql_listen_mode,
    set_sql_port,
)

if TYPE_CHECKING:
    from app.app import GPServerManager


class SQLPage(ctk.CTkFrame):
    """SQL Server configuration page."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, project: Optional[Project] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._build()

    def _build(self) -> None:
        if not self._project:
            ctk.CTkLabel(self, text="无项目数据", font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=40)
            return
        s = self._project.settings.sql

        ctk.CTkLabel(self, text="SQL Server", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        # Info card
        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill="x", padx=24, pady=(0, 12))

        fields = [
            ("实例", s.instance),
            ("端口", str(s.port)),
        ]
        for label, val in fields:
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13),
                         width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=13),
                         text_color="#79747E").pack(side="left")

        # Edit port
        port_row = ctk.CTkFrame(self, fg_color="transparent")
        port_row.pack(fill="x", padx=24, pady=(8, 4))
        ctk.CTkLabel(port_row, text="端口", font=ctk.CTkFont(size=13),
                     width=60).pack(side="left")
        self._port_entry = ctk.CTkEntry(port_row, font=ctk.CTkFont(size=13), width=100)
        self._port_entry.insert(0, str(s.port))
        self._port_entry.pack(side="left", padx=(8, 0))
        ctk.CTkButton(port_row, text="保存", width=60, height=28,
                       font=ctk.CTkFont(size=11),
                       command=self._save_port,
                       ).pack(side="left", padx=(8, 0))

        # Listen mode
        listen_row = ctk.CTkFrame(self, fg_color="transparent")
        listen_row.pack(fill="x", padx=24, pady=(8, 4))
        ctk.CTkLabel(listen_row, text="监听", font=ctk.CTkFont(size=13),
                     width=60).pack(side="left")

        self._listen_var = ctk.StringVar(value=s.listen)
        ctk.CTkRadioButton(listen_row, text="本机 (127.0.0.1)",
                           variable=self._listen_var, value="127.0.0.1",
                           font=ctk.CTkFont(size=12),
                           ).pack(side="left", padx=(8, 16))
        ctk.CTkRadioButton(listen_row, text="全部地址 (0.0.0.0)",
                           variable=self._listen_var, value="0.0.0.0",
                           font=ctk.CTkFont(size=12),
                           ).pack(side="left")

        # Actions
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkButton(act, text="← 返回仪表盘", width=110,
                       font=ctk.CTkFont(size=12),
                       command=lambda: self._app.show_dashboard(),
                       ).pack(side="left")

        ctk.CTkButton(act, text="保存配置", font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color="#6750A4", command=self._save_all,
                       ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(act, text="重启 SQL", font=ctk.CTkFont(size=13),
                       fg_color="#FF9800", command=self._restart_sql,
                       ).pack(side="right", padx=(6, 0))

        # Status
        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(8, 4))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _save_port(self) -> None:
        try:
            port = int(self._port_entry.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "端口必须是 1-65535 之间的数字")
            return

        self._project.settings.sql.port = port
        self._set_status(f"Setting SQL port to {port}…")
        threading.Thread(target=self._port_worker, args=(port,), daemon=True).start()

    def _port_worker(self, port: int) -> None:
        result = set_sql_port(port, self._project.settings.sql.instance)
        self.after(0, lambda: self._set_status(
            "OK" if "OK" in result or "n/a" in result else f"✗ {result}"))

    def _save_all(self) -> None:
        listen = self._listen_var.get()
        self._project.settings.sql.listen = listen
        try:
            port = int(self._port_entry.get().strip())
            self._project.settings.sql.port = port
        except ValueError:
            pass

        # Save to project.json
        self._project.save_json()

        mode = SqlListenMode.ALL if listen == "0.0.0.0" else SqlListenMode.LOCAL
        self._set_status("Saving SQL config…")
        threading.Thread(target=self._save_worker, args=(mode,), daemon=True).start()

    def _save_worker(self, mode: SqlListenMode) -> None:
        result = set_sql_listen_mode(mode, self._project.settings.sql.instance)
        self.after(0, lambda: self._set_status(
            "✓ 配置已保存" if "OK" in result or "n/a" in result else f"✗ {result}"))

    def _restart_sql(self) -> None:
        self._set_status("Restarting SQL Server…")
        threading.Thread(target=self._restart_worker, daemon=True).start()

    def _restart_worker(self) -> None:
        result = restart_sql(self._project.settings.sql.instance)
        self.after(0, lambda: self._set_status(result))
