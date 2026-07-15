"""Overview of the machine managed in Server Mode."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.wg_keygen import check_wg_available
from services.sql_service import get_sql_info
from services.system_service import get_system_info
from services.wireguard_service import wg_interfaces
from widgets import Card

if TYPE_CHECKING:
    from app.app import GPServerManager


class ServerDashboardPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._values: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ctk.CTkLabel(header, text="Server Dashboard", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Refresh", width=90, command=self._refresh).pack(side="right")

        # Cards grid
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=24)
        grid.grid_columnconfigure((0, 1), weight=1)

        for index, (key, title) in enumerate([
            ("system", "System"), ("sql", "SQL Server"),
            ("wireguard", "WireGuard"), ("network", "Network"),
        ]):
            card = Card(grid, title=title)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            value = ctk.CTkLabel(card, text="Loading...", justify="left", anchor="w", text_color="#79747E")
            value.pack(fill="both", expand=True, padx=16, pady=(0, 14))
            self._values[key] = value

        self._status = ctk.CTkLabel(self, text="", text_color="#79747E")
        self._status.pack(pady=8)
        self._refresh()

    def _refresh(self) -> None:
        self._status.configure(text="Refreshing local server status...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        info = get_system_info()
        sql = get_sql_info(self._app._server_project.settings.sql.instance)
        wg_error = check_wg_available()
        if wg_error:
            wireguard = "Not installed or unavailable"
        else:
            try:
                interfaces = wg_interfaces()
                wireguard = f"Active tunnels: {len(interfaces)}\n" + (", ".join(interfaces) if interfaces else "No tunnel is active")
            except Exception as exc:
                wireguard = f"Status unavailable: {exc}"
        values = {
            "system": f"{info.hostname}\n{info.os_version}\nCPU: {info.cpu_percent}%   Memory: {info.memory_percent}%\nDisk: {info.disk_percent}%   Uptime: {info.uptime_days} days",
            "sql": f"Instance: {self._app._server_project.settings.sql.instance}\nService: {sql.state}\nAgent: {sql.agent_state}\nTCP: {'enabled' if sql.tcp_enabled else 'disabled'}   Port: {sql.port}",
            "wireguard": wireguard,
            "network": f"Local IP: {info.ip_addresses or 'unavailable'}\nConfigured backup path: {self._app._server_project.settings.backup.save_path}",
        }
        self.after(0, lambda: self._apply(values))

    def _apply(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            self._values[key].configure(text=value)
        self._status.configure(text="Local server status refreshed")
