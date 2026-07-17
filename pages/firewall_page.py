"""Firewall management for the local Server Mode machine."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from services.firewall_service import WELL_KNOWN_PORTS, apply_custom_port, apply_well_known, is_rule_enabled

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

    def _card(self, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        card.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))
        if title:
            ctk.CTkLabel(card, text=title,
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=C["on_surface"],
                         ).pack(anchor="w", padx=PAD["lg"], pady=(PAD["md"], PAD["sm"]))
        return card

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Windows 防火墙",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))
        ctk.CTkLabel(self, text="仅修改 GP Server Manager 创建的规则",
                     text_color=C["outline"],
                     font=ctk.CTkFont(size=12),
                     ).pack(anchor="w", padx=PAD["xl"], pady=(0, PAD["md"]))

        # Managed rules card
        card = self._card("托管的入站规则")
        for name, port in WELL_KNOWN_PORTS.items():
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=3)
            ctk.CTkLabel(row, text=name, width=110, anchor="w",
                         font=ctk.CTkFont(size=13),
                         text_color=C["on_surface"],
                         ).pack(side="left")
            ctk.CTkLabel(row, text=f"TCP/{port}",
                         text_color=C["outline"], width=90, anchor="w",
                         font=ctk.CTkFont(size=12),
                         ).pack(side="left")
            var = ctk.BooleanVar(value=False)
            toggle = ctk.CTkSwitch(row, text="", variable=var,
                                   command=lambda n=name, v=var: self._toggle(n, v.get()))
            toggle.pack(side="right")
            self._toggles[name] = toggle

        # Custom rule card
        custom = self._card("自定义入站规则")
        row = ctk.CTkFrame(custom, fg_color="transparent")
        row.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))
        self._port = ctk.CTkEntry(row, width=110, placeholder_text="端口",
                                   fg_color=C["surface_variant"],
                                   text_color=C["on_surface"],
                                   corner_radius=6)
        self._port.pack(side="left")
        self._protocol = ctk.StringVar(value="TCP")
        ctk.CTkOptionMenu(row, values=["TCP", "UDP"], variable=self._protocol, width=80,
                          fg_color=C["surface_variant"],
                          text_color=C["on_surface"],
                          button_color=C["outline_variant"],
                          button_hover_color=C["primary_container"],
                          dropdown_fg_color=C["card_bg"],
                          ).pack(side="left", padx=PAD["sm"])
        ctk.CTkButton(row, text="添加规则", width=90,
                      fg_color=C["primary"], text_color=C["on_primary"],
                      corner_radius=8, font=ctk.CTkFont(size=12),
                      command=self._add_custom,
                      ).pack(side="left")
        if self._project:
            ctk.CTkButton(row, text="开放 WG 端口", width=120,
                          fg_color="transparent", text_color=C["on_surface_variant"],
                          hover_color=C["surface_variant"], corner_radius=8,
                          font=ctk.CTkFont(size=12),
                          command=lambda: self._add(self._project.settings.listen_port, "UDP"),
                          ).pack(side="right", padx=(PAD["sm"], 0))

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=PAD["xl"])
        ctk.CTkButton(footer, text="刷新",
                      fg_color="transparent", text_color=C["on_surface_variant"],
                      hover_color=C["surface_variant"], corner_radius=8,
                      font=ctk.CTkFont(size=12),
                      command=self._refresh,
                      ).pack(side="right")
        self._status = ctk.CTkLabel(self, text="",
                                     text_color=C["outline"],
                                     font=ctk.CTkFont(size=11))
        self._status.pack(pady=PAD["md"])
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
            messagebox.showerror("端口无效", "请输入 1-65535 之间的端口号")

    def _add(self, port: int, protocol: str) -> None:
        if not 1 <= port <= 65535:
            messagebox.showerror("端口无效", "请输入 1-65535 之间的端口号")
            return
        self._status.configure(text=f"正在添加 {protocol}/{port}...")
        threading.Thread(target=self._add_worker, args=(port, protocol), daemon=True).start()

    def _add_worker(self, port: int, protocol: str) -> None:
        result = apply_custom_port(port, protocol)
        self.after(0, lambda: self._status.configure(text=result or f"已添加 {protocol}/{port}"))

    def _refresh(self) -> None:
        self._status.configure(text="读取托管的规则...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        states = {name: is_rule_enabled(f"GP Server Manager - {name}") for name in WELL_KNOWN_PORTS}
        def update() -> None:
            for name, enabled in states.items():
                self._toggles[name].select() if enabled else self._toggles[name].deselect()
            self._status.configure(text="防火墙规则已刷新")
        self.after(0, update)
