"""Launch dialog — mode selection at startup."""
from __future__ import annotations

from typing import Optional, Tuple

import customtkinter as ctk

from app.workspace import WorkspaceMode


class WorkspaceLauncher(ctk.CTkToplevel):
    """Modal dialog shown at app start to pick server/client mode."""

    def __init__(self, parent: ctk.CTk, remember: bool = False):
        super().__init__(parent)
        self.title("GP Server Manager")
        self.geometry("460x420")
        self.resizable(False, False)

        self._result: Optional[WorkspaceMode] = None
        self._remember = remember
        self._confirmed = False

        # ── Layout ────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="GP Server Manager",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, pady=(36, 4))

        ctk.CTkLabel(
            self, text="请选择当前工作模式",
            font=ctk.CTkFont(size=14),
            text_color="#79747E",
        ).grid(row=1, column=0, pady=(0, 24))

        # Server Mode card
        self._server_var = ctk.StringVar(value="server")
        server_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#F3EDF7")
        server_card.grid(row=2, column=0, padx=40, pady=(0, 8), sticky="ew")
        server_card.bind("<Button-1>", lambda e: self._server_var.set("server"))

        rb1 = ctk.CTkRadioButton(
            server_card, text="", variable=self._server_var, value="server",
        )
        rb1.grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=12)
        ctk.CTkLabel(
            server_card, text="🖥  Server Mode",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            server_card, text="在服务器上使用  ·  SQL · WireGuard · 防火墙 · 备份",
            font=ctk.CTkFont(size=11),
            text_color="#79747E",
        ).grid(row=1, column=1, sticky="w")

        # Client Mode card
        client_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#FFF8E1")
        client_card.grid(row=3, column=0, padx=40, pady=(0, 16), sticky="ew")
        client_card.bind("<Button-1>", lambda e: self._server_var.set("client"))

        rb2 = ctk.CTkRadioButton(
            client_card, text="", variable=self._server_var, value="client",
        )
        rb2.grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=12)
        ctk.CTkLabel(
            client_card, text="💻  Client Mode",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            client_card, text="在运维电脑上使用  ·  项目管理 · 客户管理 · 配置生成",
            font=ctk.CTkFont(size=11),
            text_color="#79747E",
        ).grid(row=1, column=1, sticky="w")

        # Remember checkbox
        self._remember_var = ctk.BooleanVar(value=remember)
        ctk.CTkCheckBox(
            self, text="记住我的选择", variable=self._remember_var,
            font=ctk.CTkFont(size=13),
        ).grid(row=4, column=0, pady=(0, 20))

        # Enter button
        ctk.CTkButton(
            self, text="进入", width=160, height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._confirm,
        ).grid(row=5, column=0, pady=(0, 24))

        self.grab_set()

    def _confirm(self) -> None:
        self._confirmed = True
        self._result = WorkspaceMode(self._server_var.get())
        self.destroy()

    def result(self) -> Tuple[Optional[WorkspaceMode], bool]:
        if not self._confirmed:
            return (None, False)
        return (self._result, self._remember_var.get())
