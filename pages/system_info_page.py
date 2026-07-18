"""Diagnostics and service control for the local server."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from services.system_service import get_system_info, ping, public_ip, restart_service, service_state, traceroute

if TYPE_CHECKING:
    from app.app import GPServerManager


class SystemInfoPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, tab: str = "system", **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app, self._tab = app, tab
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="系统信息",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=PAD["xl"], pady=(0, PAD["md"]))
        self._build_system()
        self._build_services()

    def _build_system(self) -> None:
        card = ctk.CTkFrame(self._body, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        card.pack(fill="x", pady=(0, PAD["md"]))
        self._summary = ctk.CTkLabel(card, text="加载系统信息中...",
                                      justify="left", anchor="w",
                                      font=ctk.CTkFont(size=12),
                                      text_color=C["on_surface"],
                                      )
        self._summary.pack(fill="x", padx=PAD["lg"], pady=PAD["md"])

        actions = ctk.CTkFrame(self._body, fg_color="transparent")
        actions.pack(fill="x")
        ctk.CTkButton(actions, text="刷新",
                       fg_color="transparent", text_color=C["on_surface_variant"],
                       hover_color=C["surface_variant"], corner_radius=8,
                       font=ctk.CTkFont(size=12),
                       command=self._load_system,
                       ).pack(side="left")
        threading.Thread(target=self._load_system, daemon=True).start()

    def _load_system(self) -> None:
        try:
            info = get_system_info()
            lines = [
                f"主机名: {info.hostname}",
                f"系统: {info.os_version}",
                f"CPU: {info.cpu_percent}% ({info.cpu_count} 核)",
                f"内存: {info.memory_percent}% ({info.total_ram_gb:.1f} GB)",
                f"磁盘: {info.disk_percent}%",
                f"运行时间: {info.uptime_days} 天",
                f"内网 IP: {', '.join(info.ip_addresses) if info.ip_addresses else '无'}",
                f"公网 IP: {public_ip() or '获取失败'}",
            ]
            text = "\n".join(lines)
            self.after(0, lambda: self._safe_configure(self._summary, text=text))
        except Exception as exc:
            self.after(0, lambda e=exc: self._safe_configure(self._summary, text=f"获取失败: {e}"))

    def _safe_configure(self, widget, **kwargs):
        """Configure a widget only if it still exists (handles race with page destroy)."""
        try:
            if widget.winfo_exists():
                widget.configure(**kwargs)
        except Exception:
            pass

    def _build_services(self) -> None:
        self._svc_card = ctk.CTkFrame(self._body, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        self._svc_card.pack(fill="x", pady=(0, PAD["md"]))

        services = ["MSSQLSERVER", "SQLSERVERAGENT", "WinRM"]
        self._svc_labels = {}
        for svc in services:
            row = ctk.CTkFrame(self._svc_card, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=4)
            ctk.CTkLabel(row, text=svc, font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["on_surface"], width=140,
                         ).pack(side="left")
            lbl = ctk.CTkLabel(row, text="检查中…", font=ctk.CTkFont(size=12),
                                text_color=C["outline"], width=80)
            lbl.pack(side="left")
            self._svc_labels[svc] = lbl
            ctk.CTkButton(row, text="重启", width=50, height=24,
                           font=ctk.CTkFont(size=10),
                           fg_color="transparent", text_color=C["on_surface_variant"],
                           hover_color=C["surface_variant"], corner_radius=6,
                           command=lambda s=svc: self._restart_svc(s),
                           ).pack(side="right", padx=(PAD["sm"], 0))

        threading.Thread(target=self._check_svcs, daemon=True).start()

    def _check_svcs(self) -> None:
        for svc in self._svc_labels:
            try:
                state = service_state(svc)
                lbl = self._svc_labels[svc]
                self.after(0, lambda s=svc, l=lbl, st=state: self._safe_configure(
                    l, text=st, text_color=C["success"] if st == "running" else C["error"]))
            except Exception:
                pass

    def _restart_svc(self, name: str) -> None:
        self._safe_configure(self._svc_labels[name], text="重启中…", text_color=C["warning"])
        threading.Thread(target=self._restart_worker, args=(name,), daemon=True).start()

    def _restart_worker(self, name: str) -> None:
        result = restart_service(name)
        lbl = self._svc_labels[name]
        self.after(0, lambda l=lbl, r=result: self._safe_configure(
            l, text=r, text_color=C["success"] if "OK" in r else C["error"]))
