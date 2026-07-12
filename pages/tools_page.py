"""Tools page — toolbox with utility operations."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from models.project import Project
from services.system_service import ping, public_ip, restart_service, traceroute

if TYPE_CHECKING:
    from app.app import GPServerManager


class ToolsPage(ctk.CTkFrame):
    """Toolbox — Ping, Traceroute, Public IP, Service restart, etc."""

    def __init__(self, master: GPServerManager, project: Project, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = master
        self._project = project
        self._build()

    def _build(self) -> None:
        s = self._project.settings

        ctk.CTkLabel(self, text="工具箱", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        # One row = one tool card
        tools = [
            ("Ping", "测试服务器连通性", lambda: self._run_ping(s.public_ip or "8.8.8.8")),
            ("Traceroute", "追踪路由路径", lambda: self._run_traceroute(s.public_ip or "8.8.8.8")),
            ("公网 IP 检测", "检测本机公网 IP 地址", self._run_public_ip),
            ("WireGuard 重启", "重启 WireGuard 服务 (仅 Windows)", self._restart_wg),
            ("Windows 放行端口", "导航至防火墙页面", self._go_firewall),
            ("SQL 配置", "导航至 SQL 配置页面", self._go_sql),
            ("服务重启", "重启指定 Windows 服务", self._restart_service),
        ]

        for name, desc, cmd in tools:
            card = ctk.CTkFrame(self, corner_radius=12)
            card.pack(fill="x", padx=24, pady=6)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=10)

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(text_frame, text=name, font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(text_frame, text=desc, font=ctk.CTkFont(size=11),
                         text_color="#79747E", anchor="w").pack(fill="x")

            ctk.CTkButton(row, text="执行", width=80, height=32,
                           font=ctk.CTkFont(size=12), command=cmd,
                           ).pack(side="right")

        # Output area
        ctk.CTkLabel(self, text="输出", font=ctk.CTkFont(size=12, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(12, 4))

        self._output = ctk.CTkTextbox(self, height=120, corner_radius=8,
                                       font=ctk.CTkFont(size=11, family="Consolas"))
        self._output.pack(fill="x", padx=24, pady=(0, 8))

        # Back
        ctk.CTkButton(self, text="← 返回仪表盘", width=110,
                       font=ctk.CTkFont(size=12),
                       command=lambda: self._app.show_dashboard(),
                       ).pack(anchor="w", padx=24, pady=(8, 4))

    def _log(self, text: str) -> None:
        self._output.insert("end", text + "\n")
        self._output.see("end")

    def _run_ping(self, host: str) -> None:
        self._log(f"Pinging {host}…")
        threading.Thread(target=lambda: self._log(ping(host)),
                         daemon=True).start()

    def _run_traceroute(self, host: str) -> None:
        self._log(f"Traceroute to {host}…")
        threading.Thread(target=lambda: self._log(traceroute(host)),
                         daemon=True).start()

    def _run_public_ip(self) -> None:
        self._log("Detecting public IP…")
        threading.Thread(target=lambda: self._log(f"Public IP: {public_ip()}"),
                         daemon=True).start()

    def _restart_wg(self) -> None:
        self._log("WireGuard restart requires Windows.")
        # ponytail: wg-quick down/up on live interface, skip on dev

    def _go_firewall(self) -> None:
        self._app.show_firewall()

    def _go_sql(self) -> None:
        self._app.show_sql()

    def _restart_service(self) -> None:
        dlg = _ServiceDialog(self)
        self.wait_window(dlg)
        name = dlg.result()
        if name:
            self._log(f"Restarting service: {name}…")
            threading.Thread(target=lambda: self._log(restart_service(name)),
                             daemon=True).start()


class _ServiceDialog(ctk.CTkToplevel):
    """Dialog to enter a service name."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("重启服务")
        self.geometry("320x140")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="服务名称 (如 MSSQL$MSSQLSERVER)",
                     font=ctk.CTkFont(size=12)).pack(pady=(16, 8))
        self._entry = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._entry.pack(fill="x", padx=20, pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        ctk.CTkButton(btn_frame, text="取消", command=self.destroy,
                       font=ctk.CTkFont(size=12), width=80).pack(side="left")
        ctk.CTkButton(btn_frame, text="重启", command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       fg_color="#FF9800").pack(side="right")

        self._confirmed = False
        self._name = ""

    def _confirm(self) -> None:
        self._name = self._entry.get().strip()
        if self._name:
            self._confirmed = True
        self.destroy()

    def result(self) -> str:
        return self._name if self._confirmed else ""
