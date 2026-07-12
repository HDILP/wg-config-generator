"""WireGuard Server page — just status + link to official client."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.wg_keygen import check_wg_available

if TYPE_CHECKING:
    from app.app import GPServerManager

WG_DIR = Path("C:/Program Files/WireGuard")
WG_INSTALLER = Path(__file__).resolve().parent.parent / "wireguard-installer.exe"


class WireGuardServerPage(ctk.CTkFrame):
    """Server-mode WireGuard: status check, open official client, open config dir.
    
    GP Server Manager does NOT reimplement config management — the official
    WireGuard client handles import/activate/tunnel/service.
    """
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="WireGuard",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        # Status card
        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="状态",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        installed = WG_DIR.exists()
        status_color = "#4CAF50" if installed else "#B3261E"
        status_text = "✓ 已安装" if installed else "✗ 未安装"

        ctk.CTkLabel(card, text=status_text,
                     font=ctk.CTkFont(size=14),
                     text_color=status_color,
                     ).pack(anchor="w", padx=16, pady=(0, 4))

        ctk.CTkLabel(card, text=f"安装目录: {WG_DIR}" if installed else "",
                     font=ctk.CTkFont(size=11),
                     text_color="#79747E",
                     ).pack(anchor="w", padx=16, pady=(0, 10))

        # Actions
        act = ctk.CTkFrame(card, fg_color="transparent")
        act.pack(fill="x", padx=16, pady=(0, 10))

        btn = ctk.CTkButton(
            act, text="🔄 打开 WireGuard", height=32,
            font=ctk.CTkFont(size=12),
            command=self._open_wireguard,
        )
        btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            act, text="📂 配置目录", height=32,
            font=ctk.CTkFont(size=12),
            command=self._open_config_dir,
        ).pack(side="left")

        if not installed and WG_INSTALLER.exists():
            ctk.CTkButton(
                act, text="⚡ 一键安装", height=32,
                font=ctk.CTkFont(size=12),
                fg_color="#2b7a4b",
                command=self._install_wireguard,
            ).pack(side="left", padx=(8, 0))

        # Info
        info = ctk.CTkLabel(
            self,
            text="配置管理请使用官方 WireGuard 客户端。\nGP Server Manager 仅负责生成配置文件 — 部署在 Client Mode 中完成。",
            font=ctk.CTkFont(size=11),
            text_color="#79747E",
            justify="left",
        )
        info.pack(anchor="w", padx=24, pady=(8, 4))

    @staticmethod
    def _open_wireguard() -> None:
        """Launch official WireGuard client."""
        import subprocess, sys
        wg_exe = WG_DIR / "wireguard.exe"
        if wg_exe.exists():
            subprocess.Popen([str(wg_exe)], shell=True)

    @staticmethod
    def _open_config_dir() -> None:
        """Open the WireGuard config directory."""
        import subprocess, sys
        config_dir = WG_DIR / "data" / "configurations"
        if config_dir.exists():
            subprocess.Popen(["explorer", str(config_dir)], shell=True)

    @staticmethod
    def _install_wireguard() -> None:
        import platform, sys as _sys
        if platform.release().startswith("6.1"):
            from tkinter import messagebox
            messagebox.showwarning(
                "Win7 需要补丁",
                "当前系统为 Windows 7。\n\n"
                "WireGuard 官方安装程序需要两个补丁：\n"
                "• KB2921916 — 驱动签名信任\n"
                "• KB3033929 — SHA-256 证书支持\n\n"
                "请使用 Client Mode 生成部署包，\n"
                "部署包已包含自动安装脚本（install_win7.bat）。"
            )
            return
        import subprocess
        subprocess.Popen([str(WG_INSTALLER)], shell=True)
