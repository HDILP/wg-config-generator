"""Server Dashboard — 4-pill overview with status bar."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from core.wg_keygen import check_wg_available
from services.sql_service import get_sql_info
from services.system_service import get_system_info
from services.wireguard_service import wg_interfaces
from utils.icon_loader import load_icon

if TYPE_CHECKING:
    from app.app import GPServerManager


class ServerDashboardPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._info: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        ctk.CTkLabel(
            header, text="Server Dashboard",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(side="left")

        refresh_icon = load_icon("refresh-cw", size=16, color=C["on_surface_variant"])
        ctk.CTkButton(
            header, text="", image=refresh_icon, width=32, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["on_surface_variant"],
            hover_color=C["surface_variant"],
            corner_radius=8,
            command=self._refresh,
        ).pack(side="right")

        # 4 pills row
        pills_frame = ctk.CTkFrame(self, fg_color=C["container_bg"], corner_radius=CR)
        pills_frame.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))

        self._pills: dict[str, dict] = {}
        pill_data = [
            ("CPU", "cpu", "server"),
            ("内存", "memory", "hard-drive"),
            ("磁盘", "disk", "hard-drive"),
            ("服务", "services", "activity"),
        ]

        for i, (label, key, icon_name) in enumerate(pill_data):
            pill = ctk.CTkFrame(pills_frame, fg_color=C["card_bg"], corner_radius=CR, border_width=1, border_color=C["outline_variant"])
            pill.grid(row=0, column=i, sticky="nsew", padx=4, pady=PAD["md"])
            pills_frame.grid_columnconfigure(i, weight=1)

            if i == 0:
                icon = load_icon(icon_name, size=20, color=C["primary"])
            elif i == 1:
                icon = load_icon(icon_name, size=20, color=C["primary"])
            elif i == 2:
                icon = load_icon(icon_name, size=20, color=C["primary"])
            else:
                icon = load_icon(icon_name, size=20, color=C["primary"])

            ico = ctk.CTkLabel(pill, text="", image=icon)
            ico.pack(pady=(PAD["lg"], 0))

            value_lbl = ctk.CTkLabel(
                pill, text="—",
                font=ctk.CTkFont(size=26, weight="bold"),
                text_color=C["primary"],
            )
            value_lbl.pack(pady=(PAD["sm"], 0))

            label_lbl = ctk.CTkLabel(
                pill, text=label,
                font=ctk.CTkFont(size=11),
                text_color=C["outline"],
            )
            label_lbl.pack(pady=(0, PAD["lg"]))

            self._pills[key] = {
                "value": value_lbl,
                "label": label_lbl,
            }

        # Bottom status bar
        status_frame = ctk.CTkFrame(self, fg_color=C["card_bg"], corner_radius=CR, border_width=1, border_color=C["outline_variant"])
        status_frame.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))

        self._status_labels: dict[str, ctk.CTkLabel] = {}
        status_keys = [
            ("SQL", "database"),
            ("WireGuard", "lock"),
            ("网络", "activity"),
            ("系统", "server"),
        ]
        for label, icon_name in status_keys:
            icon = load_icon(icon_name, size=14, color=C["outline"])
            row = ctk.CTkFrame(status_frame, fg_color="transparent")
            row.pack(side="left", fill="x", expand=True, padx=PAD["md"], pady=PAD["md"])

            ctk.CTkLabel(row, text="", image=icon).pack(side="left", padx=(0, PAD["sm"]))
            lbl = ctk.CTkLabel(
                row, text=f"{label}: 加载中…",
                font=ctk.CTkFont(size=11),
                text_color=C["on_surface_variant"],
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)
            self._status_labels[label] = lbl

        self._status = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
            text_color=C["outline"],
        )
        self._status.pack(pady=(0, PAD["md"]))

        # Auto-refresh on load
        self._refresh()

    def _set_pill(self, key: str, value: str, color: str = C["primary"]) -> None:
        if key in self._pills:
            self._pills[key]["value"].configure(text=value, text_color=color)

    def _set_status(self, key: str, text: str, ok: bool = True) -> None:
        color = C["success"] if ok else C["error"]
        if key in self._status_labels:
            prefix = "✓" if ok else "✗"
            self._status_labels[key].configure(
                text=f"{prefix}  {text}",
                text_color=color,
            )

    def _refresh(self) -> None:
        self._status.configure(text="Refreshing…")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            info = get_system_info()
            cpu_pct = info.cpu_percent
            mem_pct = info.memory_percent
            disk_pct = info.disk_percent
            uptime = info.uptime_days

            cpu_color = C["success"] if cpu_pct < 50 else C["warning"] if cpu_pct < 80 else C["error"]
            mem_color = C["success"] if mem_pct < 50 else C["warning"] if mem_pct < 80 else C["error"]
            disk_color = C["success"] if disk_pct < 50 else C["warning"] if disk_pct < 80 else C["error"]

            self.after(0, lambda: self._set_pill("cpu", f"{cpu_pct}%", cpu_color))
            self.after(0, lambda: self._set_pill("memory", f"{mem_pct}%", mem_color))
            self.after(0, lambda: self._set_pill("disk", f"{disk_pct}%", disk_color))
            svc_ok = info.memory_percent < 90  # simplistic health indicator
            self.after(0, lambda: self._set_pill(
                "services", "✓" if svc_ok else "⚠",
                C["success"] if svc_ok else C["warning"],
            ))

            # Status bar
            self.after(0, lambda: self._set_status(
                "系统", f"{info.hostname} · {uptime}d", ok=True))

            try:
                sql = get_sql_info(self._app._server_project.settings.sql.instance)
                self.after(0, lambda: self._set_status(
                    "SQL", f"{sql.state}", ok=sql.state == "running"))
            except Exception:
                self.after(0, lambda: self._set_status("SQL", "unavailable", ok=False))

            try:
                wg_error = check_wg_available()
                if wg_error:
                    self.after(0, lambda: self._set_status("WireGuard", "not installed", ok=False))
                else:
                    interfaces = wg_interfaces()
                    wg_text = f"{len(interfaces)} tunnel{'s' if len(interfaces) != 1 else ''}" if interfaces else "inactive"
                    self.after(0, lambda: self._set_status("WireGuard", wg_text, ok=bool(interfaces)))
            except Exception:
                self.after(0, lambda: self._set_status("WireGuard", "error", ok=False))

            ip_text = info.ip_addresses or "unavailable"
            self.after(0, lambda: self._set_status("网络", ip_text, ok=True))

            self.after(0, lambda: self._app.show_toast("✓ 仪表盘已刷新", "success"))

        except Exception as exc:
            self.after(0, lambda: self._set_pill("cpu", "?", C["error"]))
            self.after(0, lambda: self._set_pill("memory", "?", C["error"]))
            self.after(0, lambda: self._set_pill("disk", "?", C["error"]))
            self.after(0, lambda: self._set_pill("services", "✗", C["error"]))

        self.after(0, lambda: self._status.configure(text=""))
