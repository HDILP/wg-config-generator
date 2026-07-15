"""Settings page — global app settings with workspace mode selector."""
from __future__ import annotations

import sys as _sys
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.theme import ThemeMode
from app.workspace import WorkspaceMode, nav_for_mode
from models.app_settings import AppSettings
from widgets import Card, PrimaryButton

if TYPE_CHECKING:
    from app.app import GPServerManager


class SettingsPage(ctk.CTkFrame):
    """Global settings: workspace mode, theme, projects dir, language."""
    WORKSPACE = WorkspaceMode.BOTH

    def __init__(
        self, master,
        app: GPServerManager,
        settings: AppSettings,
        current_workspace: WorkspaceMode,
        **kwargs,
    ):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._settings = settings
        self._current_workspace = current_workspace
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="设置", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        # ═══ Workspace Mode ═══════════════════════════════════════
        ws_card = Card(self, title="工作模式")
        ws_card.pack(fill="x", padx=24, pady=(0, 12))

        frame = ctk.CTkFrame(ws_card, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(0, 10))

        # Radio: Server
        ws_server = ctk.CTkRadioButton(
            frame, text="🖥  Server Mode（服务器本机使用）",
            variable=self._ws_var(), value="server",
            font=ctk.CTkFont(size=13),
            command=self._on_ws_change,
        )
        ws_server.pack(anchor="w", pady=2)

        # Radio: Client
        ws_client = ctk.CTkRadioButton(
            frame, text="💻  Client Mode（运维电脑使用）",
            variable=self._ws_var(), value="client",
            font=ctk.CTkFont(size=13),
            command=self._on_ws_change,
        )
        ws_client.pack(anchor="w", pady=2)

        # Radio: Ask
        ws_ask = ctk.CTkRadioButton(
            frame, text="启动时询问",
            variable=self._ws_var(), value="ask",
            font=ctk.CTkFont(size=13),
            command=self._on_ws_change,
        )
        ws_ask.pack(anchor="w", pady=2)

        # ═══ Theme ════════════════════════════════════════════════
        theme_card = Card(self, title="外观")
        theme_card.pack(fill="x", padx=24, pady=(0, 12))

        theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(theme_row, text="主题", font=ctk.CTkFont(size=13),
                     width=80).pack(side="left")
        theme_map = {"light": "浅色", "dark": "深色", "system": "跟随系统"}
        theme_rev = {v: k for k, v in theme_map.items()}
        self._theme_var = ctk.StringVar(
            value=theme_map.get(self._settings.theme, "浅色"),
        )
        ctk.CTkOptionMenu(
            theme_row, values=["浅色", "深色", "跟随系统"],
            variable=self._theme_var,
            font=ctk.CTkFont(size=12),
            command=self._change_theme,
        ).pack(side="left", padx=(8, 0))

        # ═══ Language ════════════════════════════════════════════
        lang_card = Card(self, title="语言")
        lang_card.pack(fill="x", padx=24, pady=(0, 12))

        lang_row = ctk.CTkFrame(lang_card, fg_color="transparent")
        lang_row.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(lang_row, text="界面语言", font=ctk.CTkFont(size=13),
                     width=80).pack(side="left")
        ctk.CTkLabel(lang_row, text="简体中文",
                     font=ctk.CTkFont(size=13),
                     text_color="#79747E").pack(side="left")

        # ═══ About ═══════════════════════════════════════════════
        sep = ctk.CTkLabel(self, text="─" * 40, text_color="#79747E",
                            font=ctk.CTkFont(size=10))
        sep.pack(pady=(8, 8))

        about = Card(self, title="关于")
        about.pack(fill="x", padx=24)

        for label, val in [
            ("GP Server Manager", "v2.0 — Workspace"),
            ("Python", _sys.version.split()[0]),
            ("UI Framework", "CustomTkinter"),
        ]:
            row = ctk.CTkFrame(about, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         width=120).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         text_color="#79747E").pack(side="left")

        # ═══ Footer ══════════════════════════════════════════════
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkButton(footer, text="← 返回首页", width=110,
                       font=ctk.CTkFont(size=12),
                       command=self._go_back,
                       ).pack(side="left")

        PrimaryButton(footer, text="💾 保存设置", font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color="#6750A4",
                      command=self._save).pack(side="right")

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(4, 8))

    def _ws_var(self) -> ctk.StringVar:
        if not hasattr(self, "_ws_var_inner"):
            mode = self._settings.workspace_mode
            self._ws_var_inner = ctk.StringVar(value=mode)
        return self._ws_var_inner

    def _on_ws_change(self) -> None:
        pass  # applied on save

    def _change_theme(self, choice: str) -> None:
        mapping = {"浅色": "light", "深色": "dark", "跟随系统": "system"}
        mode = mapping.get(choice, "light")
        ctk.set_appearance_mode(mode)
        self._settings.theme = mode

    def _go_back(self) -> None:
        self._app._nav_to_home()

    def _save(self) -> None:
        self._settings.workspace_mode = self._ws_var().get()
        self._settings.theme = {
            "浅色": "light", "深色": "dark", "跟随系统": "system",
        }.get(self._theme_var.get(), "light")
        self._settings.save()
        self._status.configure(text="✓ 设置已保存")

        changed = self._settings.workspace_mode != self._current_workspace.value
        if changed and self._settings.workspace_mode != "ask":
            import tkinter.messagebox as mb
            if mb.askyesno("重启", "工作模式已更改，重启程序后生效？"):
                import os, sys as _sys2
                _sys2.platform == "win32" and os.execl(
                    _sys2.executable, _sys2.executable, *_sys2.argv,
                )
