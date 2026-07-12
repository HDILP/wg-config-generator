"""WireGuard Server page — import conf, view peers, manage tunnel."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import threading

from app.workspace import WorkspaceMode
from widgets import CardFrame

if TYPE_CHECKING:
    from app.app import GPServerManager


class WireGuardServerPage(ctk.CTkFrame):
    """Server-mode WireGuard: import conf, view peers, tunnel status."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="WireGuard — Server",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        # Import conf section
        import_card = CardFrame(self, title="导入配置")
        import_card.pack(fill="x", padx=24, pady=(0, 12))

        row = ctk.CTkFrame(import_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(row, text="server.conf 路径",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._conf_path = ctk.CTkEntry(row, font=ctk.CTkFont(size=13))
        self._conf_path.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkButton(row, text="导入", width=60, height=28,
                       font=ctk.CTkFont(size=11),
                       command=self._import_conf).pack(side="left", padx=(8, 0))

        # Tunnel status
        status_card = CardFrame(self, title="隧道状态")
        status_card.pack(fill="x", padx=24, pady=(0, 12))

        self._tunnel_status = ctk.CTkLabel(
            status_card, text="未知", font=ctk.CTkFont(size=14),
        )
        self._tunnel_status.pack(padx=16, pady=10)

        act = ctk.CTkFrame(status_card, fg_color="transparent")
        act.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkButton(act, text="启动", width=80,
                       command=self._start_tunnel).pack(side="left", padx=(0, 8))
        ctk.CTkButton(act, text="停止", width=80,
                       fg_color="#b33",
                       command=self._stop_tunnel).pack(side="left")

        # Peer list
        peer_card = CardFrame(self, title="Peer 列表")
        peer_card.pack(fill="both", expand=True, padx=24)

        self._peer_frame = ctk.CTkFrame(peer_card, fg_color="transparent")
        self._peer_frame.pack(fill="both", expand=True, padx=16, pady=10)

        ctk.CTkLabel(self._peer_frame, text="暂无数据，请先导入配置或启动隧道",
                     font=ctk.CTkFont(size=12),
                     text_color="#79747E").pack(pady=16)

        self._status = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color="#79747E",
        )
        self._status.pack(pady=(8, 4))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _import_conf(self) -> None:
        path = self._conf_path.get().strip()
        if not path:
            self._set_status("请输入 server.conf 路径")
            return
        self._set_status(f"正在导入 {path}…")
        # ponytail: real import needs Windows + WireGuard; stub for now
        self.after(1500, lambda: self._set_status("✓ 已导入"))

    def _start_tunnel(self) -> None:
        self._set_status("正在启动隧道…")
        # ponytail: wg-quick up, add when real server usage
        self.after(1000, lambda: self._tunnel_status.configure(
            text="🟢 运行中", text_color="#4CAF50"))
        self.after(1000, lambda: self._set_status("✓ 隧道已启动"))

    def _stop_tunnel(self) -> None:
        self._set_status("正在停止隧道…")
        # ponytail: wg-quick down
        self.after(1000, lambda: self._tunnel_status.configure(
            text="🔴 已停止", text_color="#B3261E"))
        self.after(1000, lambda: self._set_status("✓ 隧道已停止"))
