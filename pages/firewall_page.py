"""Firewall management for the local Server Mode machine."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from services.firewall_service import WELL_KNOWN_PORTS, apply_custom_port, apply_well_known, is_rule_enabled
from widgets import Card, FieldRow, PrimaryButton

if TYPE_CHECKING:
    from app.app import GPServerManager


class FirewallPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, project=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._toggles: dict[str, ctk.CTkSwitch] = {}
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Windows Firewall", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(self, text="Only rules created by GP Server Manager are changed.", text_color="#79747E").pack(anchor="w", padx=24, pady=(0, 16))

        card = Card(self, title="Managed inbound rules")
        card.pack(fill="x", padx=24)
        for name, port in WELL_KNOWN_PORTS.items():
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=name, width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"TCP/{port}", text_color="#79747E", width=90, anchor="w").pack(side="left")
            var = ctk.BooleanVar(value=False)
            toggle = ctk.CTkSwitch(row, text="", variable=var, command=lambda n=name, v=var: self._toggle(n, v.get()))
            toggle.pack(side="right")
            self._toggles[name] = toggle

        custom = Card(self, title="Custom inbound rule")
        custom.pack(fill="x", padx=24, pady=12)
        row = ctk.CTkFrame(custom, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        self._port = ctk.CTkEntry(row, width=110, placeholder_text="Port")
        self._port.pack(side="left")
        self._protocol = ctk.StringVar(value="TCP")
        ctk.CTkOptionMenu(row, values=["TCP", "UDP"], variable=self._protocol, width=80).pack(side="left", padx=8)
        PrimaryButton(row, text="Add rule", width=90, command=self._add_custom).pack(side="left")
        if self._project:
            ctk.CTkButton(row, text="Open WireGuard port", width=140,
                          command=lambda: self._add(self._project.settings.listen_port, "UDP")).pack(side="right")
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=24)
        PrimaryButton(footer, text="Refresh", command=self._refresh).pack(side="right")
        self._status = ctk.CTkLabel(self, text="", text_color="#79747E")
        self._status.pack(pady=8)
        self._refresh()

    def _toggle(self, name: str, enabled: bool) -> None:
        self._status.configure(text=f"Updating {name}...")
        threading.Thread(target=self._toggle_worker, args=(name, enabled), daemon=True).start()

    def _toggle_worker(self, name: str, enabled: bool) -> None:
        result = apply_well_known(name, enabled)
        self.after(0, lambda: self._status.configure(text=result or f"Updated {name}"))
        self.after(0, self._refresh)

    def _add_custom(self) -> None:
        try:
            self._add(int(self._port.get()), self._protocol.get())
        except ValueError:
            messagebox.showerror("Invalid port", "Enter a port from 1 to 65535.")

    def _add(self, port: int, protocol: str) -> None:
        if not 1 <= port <= 65535:
            messagebox.showerror("Invalid port", "Enter a port from 1 to 65535.")
            return
        self._status.configure(text=f"Adding {protocol}/{port}...")
        threading.Thread(target=self._add_worker, args=(port, protocol), daemon=True).start()

    def _add_worker(self, port: int, protocol: str) -> None:
        result = apply_custom_port(port, protocol)
        self.after(0, lambda: self._status.configure(text=result or f"Added {protocol}/{port}"))

    def _refresh(self) -> None:
        self._status.configure(text="Reading managed rules...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        states = {name: is_rule_enabled(f"GP Server Manager - {name}") for name in WELL_KNOWN_PORTS}
        def update() -> None:
            for name, enabled in states.items():
                self._toggles[name].select() if enabled else self._toggles[name].deselect()
            self._status.configure(text="Firewall rule status refreshed")
        self.after(0, update)
