"""Dashboard page — project overview with status indicators and security score."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from models.project import Project
from widgets import CardFrame, SecurityScoreWidget, StatusIndicator

if TYPE_CHECKING:
    from app.app import GPServerManager


class DashboardPage(ctk.CTkFrame):
    """Project dashboard — status overview, security score, quick info."""

    def __init__(self, master: GPServerManager, project: Project, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = master
        self._project = project
        self._build()

    def _build(self) -> None:
        s = self._project.settings

        # Title
        title = ctk.CTkFrame(self, fg_color="transparent")
        title.pack(fill="x", padx=24, pady=(20, 16))
        ctk.CTkLabel(
            title, text=s.name,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            title, text=f"  |  {s.public_ip or '未设置公网IP'}",
            font=ctk.CTkFont(size=14),
            text_color="#79747E",
        ).pack(side="left", padx=(8, 0))

        # Two-column layout
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24)

        # Left: status cards
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Status card
        card = CardFrame(left, title="服务器状态")
        card.pack(fill="x", pady=(0, 12))

        items = [
            ("备份中心", "ok" if self._project.settings.backup.enabled else "warning"),
            ("WireGuard", "ok" if self._project.server_keypair.public else "unknown"),
            ("SQL Server", "unknown"),
            ("Windows 防火墙", "unknown"),
            ("远程协助", "ok" if s.ops.remote_id or s.remote.id else "warning"),
        ]
        for label, status in items:
            si = StatusIndicator(card, label, status)
            si.pack(fill="x", padx=16, pady=4)

        # Quick info
        info_card = CardFrame(left, title="服务器信息")
        info_card.pack(fill="x", pady=(0, 12))

        fields = [
            ("VPN 地址", s.vpn_ip),
            ("子网", s.subnet),
            ("监听端口", str(s.listen_port)),
            ("客户数", str(len(self._project.clients))),
            ("区域", s.ops.region or "未设置"),
            ("负责人", s.ops.contact or "未设置"),
        ]
        for label, val in fields:
            row = ctk.CTkFrame(info_card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         text_color="#79747E", width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Right: security score
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="right", fill="y", padx=(12, 0))

        score_items = [
            {"label": "WireGuard 已配置", "ok": bool(self._project.server_keypair.public)},
            {"label": "SQL 未开放公网", "ok": s.sql.listen == "127.0.0.1"},
            {"label": "Windows 防火墙", "ok": True},
            {"label": "RDP 已限制", "ok": False},
            {"label": "SMB 已关闭", "ok": True},
        ]
        ok_count = sum(1 for x in score_items if x["ok"])
        score = int((ok_count / len(score_items)) * 100)

        score_widget = SecurityScoreWidget(right, score=score, items=score_items)
        score_widget.pack(fill="x", pady=(0, 12))

        btn_kw = dict(height=36, corner_radius=8, font=ctk.CTkFont(size=12))
        ctk.CTkButton(right, text="🛠  立即修复", **btn_kw,
                       command=lambda: self._app.show_wireguard()).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(right, text="🔄  自动修复", fg_color="gray50",
                       hover_color="gray40", **btn_kw,
                       command=lambda: self._app.set_status("自动修复功能开发中")).pack(fill="x")
