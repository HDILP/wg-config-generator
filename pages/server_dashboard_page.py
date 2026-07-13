"""Server Dashboard — real-time server status for Server Mode."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import threading

from app.workspace import WorkspaceMode
from core.wg_keygen import check_wg_available
from services.system_service import get_system_info
from widgets import CardFrame, StatusIndicator

if TYPE_CHECKING:
    from app.app import GPServerManager


def _svc_status(name: str) -> str:
    """Check Windows service status via sc query."""
    import subprocess, sys
    if sys.platform != "win32":
        return "unknown"
    try:
        r = subprocess.run(["sc", "query", name], capture_output=True,
                           text=True, timeout=10)
        return "ok" if "RUNNING" in r.stdout else "error"
    except Exception:
        return "unknown"


def _fw_status() -> str:
    """Check if Windows Firewall is on."""
    import subprocess, sys
    if sys.platform != "win32":
        return "unknown"
    try:
        r = subprocess.run(["netsh", "advfirewall", "show", "currentprofile"],
                           capture_output=True, text=True, timeout=10)
        return "ok" if "ON" in r.stdout.upper() else "error"
    except Exception:
        return "unknown"


def _backup_status() -> str:
    """Check if any GP Backup scheduled task exists."""
    import subprocess, sys
    if sys.platform != "win32":
        return "unknown"
    try:
        r = subprocess.run(["schtasks", "/query", "/tn", "GPBackup*"],
                           capture_output=True, text=True, timeout=10)
        return "ok" if "GPBackup" in r.stdout else "warning"
    except Exception:
        return "unknown"


class ServerDashboardPage(ctk.CTkFrame):
    """Server mode dashboard: real-time CPU, memory, disk, service status."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._indicators: dict[str, StatusIndicator] = {}
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Server Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24)

        left = ctk.CTkFrame(main, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        # Left column: service cards
        svc_card = CardFrame(left, title="服务状态")
        svc_card.pack(fill="x", pady=(0, 12))

        for label, key in [
            ("SQL Server", "sql"),
            ("WireGuard", "wireguard"),
            ("Windows 防火墙", "firewall"),
            ("自动备份", "backup"),
        ]:
            si = StatusIndicator(svc_card, label, "unknown")
            si.pack(fill="x", padx=16, pady=4)
            self._indicators[key] = si

        # Right column: system info
        sys_card = CardFrame(right, title="系统信息")
        sys_card.pack(fill="x", pady=(0, 12))

        self._sys_rows = {}
        for label in ["CPU", "内存", "磁盘", "网络"]:
            row = ctk.CTkFrame(sys_card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         text_color="#79747E", width=60).pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=12),
                               anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self._sys_rows[label] = val

        # Refresh button
        ctk.CTkButton(
            self, text="🔄 刷新状态", width=120,
            font=ctk.CTkFont(size=12),
            command=self._refresh,
        ).pack(anchor="w", padx=24, pady=(8, 4))

        self._status = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color="#79747E",
        )
        self._status.pack(pady=(4, 8))

        # Auto-refresh on startup
        self._refresh()

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _refresh(self) -> None:
        self._set_status("加载中…")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            # System info
            info = get_system_info()
            def _set(k, v):
                self._sys_rows[k].configure(text=f"{v}%" if v else "N/A")
            self.after(0, lambda: _set("CPU", info.cpu_percent))
            self.after(0, lambda: _set("内存", info.memory_percent))
            self.after(0, lambda: _set("磁盘", info.disk_percent))

            # Service statuses
            svc_map = {
                "sql": _svc_status("MSSQL$MSSQLSERVER"),
                "wireguard": "ok" if not check_wg_available() else "error",
                "firewall": _fw_status(),
                "backup": _backup_status(),
            }
            for key, status in svc_map.items():
                self.after(0, lambda k=key, s=status: self._indicators[k].set_status(s))

            self.after(0, lambda: self._set_status("✓ 已刷新"))
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"✗ {exc}"))
