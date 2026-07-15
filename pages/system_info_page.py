"""Diagnostics and service control for the local server."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from services.system_service import get_system_info, ping, public_ip, restart_service, service_state, traceroute
from widgets import Card, PrimaryButton

if TYPE_CHECKING:
    from app.app import GPServerManager


class SystemInfoPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, tab: str = "system", **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app, self._tab = app, tab
        self._build()

    def _build(self) -> None:
        title = "System information" if self._tab == "system" else "Service management"
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=24, pady=(20, 12))
        tabs = ctk.CTkFrame(self, fg_color="transparent")
        tabs.pack(fill="x", padx=24)
        self._tab_var = ctk.StringVar(value=self._tab)
        for text, value in (("System information", "system"), ("Service management", "services")):
            ctk.CTkRadioButton(tabs, text=text, variable=self._tab_var, value=value, command=self._switch).pack(side="left", padx=(0, 16))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=24, pady=12)
        self._switch()

    def _switch(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        if self._tab_var.get() == "system":
            self._build_system()
        else:
            self._build_services()

    def _build_system(self) -> None:
        self._summary = ctk.CTkLabel(self._body, text="Loading system information...", justify="left", anchor="w")
        self._summary.pack(fill="x", pady=(0, 12))
        actions = ctk.CTkFrame(self._body, fg_color="transparent")
        actions.pack(fill="x")
        PrimaryButton(actions, text="Refresh", command=self._load_system).pack(side="left")
        PrimaryButton(actions, text="Ping 8.8.8.8", command=lambda: self._diagnose("Ping", ping, "8.8.8.8")).pack(side="left", padx=8)
        PrimaryButton(actions, text="Trace route", command=lambda: self._diagnose("Trace route", traceroute, "8.8.8.8")).pack(side="left")
        PrimaryButton(actions, text="Detect public IP", command=lambda: self._diagnose("Public IP", public_ip)).pack(side="left", padx=8)
        self._output = ctk.CTkTextbox(self._body, corner_radius=12, font=ctk.CTkFont(family="Consolas", size=11))
        self._output.pack(fill="both", expand=True, pady=12)
        self._load_system()

    def _load_system(self) -> None:
        threading.Thread(target=self._load_system_worker, daemon=True).start()

    def _load_system_worker(self) -> None:
        info = get_system_info()
        try:
            external = public_ip()
        except Exception:
            external = "unavailable"
        text = (f"Host: {info.hostname}\nOS: {info.os_version}\nCPU: {info.cpu_count} cores, {info.cpu_percent}%\n"
                f"Memory: {info.memory_percent}% of {info.total_ram_gb} GB\nDisk: {info.disk_percent}%\n"
                f"Uptime: {info.uptime_days} days\nLocal IP: {info.ip_addresses or 'unavailable'}\nPublic IP: {external}")
        self.after(0, lambda: self._summary.configure(text=text))

    def _diagnose(self, label, func, *args) -> None:
        self._output.insert("end", f"\n> {label}...\n")
        threading.Thread(target=self._diagnose_worker, args=(func, args), daemon=True).start()

    def _diagnose_worker(self, func, args) -> None:
        try:
            result = func(*args)
        except Exception as exc:
            result = f"Error: {exc}"
        self.after(0, lambda: (self._output.insert("end", result + "\n"), self._output.see("end")))

    def _build_services(self) -> None:
        ctk.CTkLabel(self._body, text="Restart is performed only after the service state has been checked.", text_color="#79747E").pack(anchor="w", pady=(0, 8))
        self._service_rows: dict[str, ctk.CTkLabel] = {}
        instance = self._app._server_project.settings.sql.instance
        sql_service = "MSSQLSERVER" if instance.upper() == "MSSQLSERVER" else f"MSSQL${instance}"
        agent_service = "SQLSERVERAGENT" if instance.upper() == "MSSQLSERVER" else f"SQLAgent${instance}"
        services = [(sql_service, f"SQL Server ({instance})"), (agent_service, "SQL Server Agent"), ("WireGuardManager", "WireGuard Manager")]
        card = Card(self._body, corner_radius=12)
        card.pack(fill="x")
        for service, label in services:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(row, text=label, width=210, anchor="w").pack(side="left")
            state = ctk.CTkLabel(row, text="Checking...", text_color="#79747E")
            state.pack(side="left", fill="x", expand=True)
            self._service_rows[service] = state
            PrimaryButton(row, text="Restart", width=80, command=lambda s=service: self._restart(s)).pack(side="right")
        self._service_status = ctk.CTkLabel(self._body, text="", text_color="#79747E")
        self._service_status.pack(pady=10)
        self._refresh_services()

    def _refresh_services(self) -> None:
        threading.Thread(target=self._service_worker, daemon=True).start()

    def _service_worker(self) -> None:
        states = {name: service_state(name) for name in self._service_rows}
        self.after(0, lambda: [self._service_rows[name].configure(text=value) for name, value in states.items()])

    def _restart(self, service: str) -> None:
        self._service_status.configure(text=f"Restarting {service}...")
        threading.Thread(target=self._restart_worker, args=(service,), daemon=True).start()

    def _restart_worker(self, service: str) -> None:
        result = restart_service(service)
        self.after(0, lambda: (self._service_status.configure(text=result), self._refresh_services()))
