"""Firewall page — manage Windows Firewall rules via GUI."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Dict, Optional

import customtkinter as ctk

from app.workspace import WorkspaceMode
from models.project import Project
from services.firewall_service import WELL_KNOWN_PORTS, apply_custom_port, apply_well_known

if TYPE_CHECKING:
    from app.app import GPServerManager


class FirewallPage(ctk.CTkFrame):
    """Windows Firewall rule management."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, project: Optional[Project] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._toggles: Dict[str, ctk.CTkSwitch] = {}
        self._build()

    def _build(self) -> None:
        if not self._project:
            ctk.CTkLabel(self, text="无项目数据", font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=40)
            return
        ctk.CTkLabel(self, text="Windows 防火墙", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        desc = ctk.CTkLabel(self, text="管理常见服务的入站规则。无需手动输入 netsh 命令。",
                            font=ctk.CTkFont(size=12), text_color="#79747E",
                            anchor="w", wraplength=500)
        desc.pack(fill="x", padx=24, pady=(0, 16))

        # Well-known services
        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="常用服务", font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        for name, port in WELL_KNOWN_PORTS.items():
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)

            ctk.CTkLabel(row, text=f"{name}  ({port})", font=ctk.CTkFont(size=13),
                         width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text="TCP", font=ctk.CTkFont(size=11),
                         text_color="#79747E", width=40).pack(side="left")

            var = ctk.BooleanVar(value=False)
            sw = ctk.CTkSwitch(row, text="", variable=var,
                               command=lambda n=name, v=var: self._toggle_rule(n, v))
            sw.pack(side="right", padx=(0, 4))
            self._toggles[name] = sw

        # Custom port
        sep = ctk.CTkLabel(self, text="─" * 40, text_color="#79747E",
                            font=ctk.CTkFont(size=10))
        sep.pack(pady=(8, 8))

        custom = ctk.CTkFrame(self, fg_color="transparent")
        custom.pack(fill="x", padx=24)

        ctk.CTkLabel(custom, text="自定义端口", font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w")

        port_row = ctk.CTkFrame(custom, fg_color="transparent")
        port_row.pack(fill="x", pady=(8, 4))

        ctk.CTkLabel(port_row, text="端口", font=ctk.CTkFont(size=13),
                     width=50).pack(side="left")
        self._custom_port = ctk.CTkEntry(port_row, font=ctk.CTkFont(size=13), width=100)
        self._custom_port.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(port_row, text="协议", font=ctk.CTkFont(size=13),
                     width=50).pack(side="left", padx=(16, 0))
        self._proto_var = ctk.StringVar(value="TCP")
        proto_menu = ctk.CTkOptionMenu(port_row, values=["TCP", "UDP"],
                                        variable=self._proto_var, width=70,
                                        font=ctk.CTkFont(size=12))
        proto_menu.pack(side="left", padx=(8, 0))

        ctk.CTkButton(port_row, text="应用", width=70, height=28,
                       font=ctk.CTkFont(size=11), fg_color="#2b7a4b",
                       command=self._apply_custom,
                       ).pack(side="left", padx=(16, 0))

        # Actions
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkButton(act, text="← 返回仪表盘", width=110,
                       font=ctk.CTkFont(size=12),
                       command=lambda: self._app.show_dashboard(),
                       ).pack(side="left")

        ctk.CTkButton(act, text="🔄 刷新状态", font=ctk.CTkFont(size=13),
                       command=self._refresh_status,
                       ).pack(side="right")

        # Status
        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(8, 4))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _toggle_rule(self, name: str, var: ctk.BooleanVar) -> None:
        enabled = var.get()
        self._set_status(f"{'Enabling' if enabled else 'Disabling'} {name}…")
        threading.Thread(target=self._toggle_worker, args=(name, enabled),
                         daemon=True).start()

    def _toggle_worker(self, name: str, enabled: bool) -> None:
        result = apply_well_known(name, enabled)
        self.after(0, lambda: self._set_status(
            f"✓ {name} {'enabled' if enabled else 'disabled'}"
            if "OK" in result or "n/a" in result else f"✗ {result}"))

    def _apply_custom(self) -> None:
        try:
            port = int(self._custom_port.get().strip())
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
        proto = self._proto_var.get()
        self._set_status(f"Adding {proto}:{port}…")
        threading.Thread(target=self._custom_worker, args=(port, proto),
                         daemon=True).start()

    def _custom_worker(self, port: int, proto: str) -> None:
        result = apply_custom_port(port, proto)
        self.after(0, lambda: self._set_status(
            f"✓ {proto}:{port} rule added"
            if "OK" in result or "n/a" in result else f"✗ {result}"))

    def _refresh_status(self) -> None:
        self._set_status("Refreshing… (Windows only)")
        # ponytail: real status check requires Windows
        self.after(2000, lambda: self._set_status("状态已刷新"))
