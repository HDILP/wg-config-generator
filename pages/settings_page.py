"""Settings page — global app settings with workspace mode selector."""
from __future__ import annotations

import sys as _sys
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode, nav_for_mode
from models.app_settings import AppSettings
from utils.icon_loader import load_icon

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

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        card.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))
        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["lg"], pady=(PAD["md"], PAD["sm"]))
        return card

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="设置",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        # ═══ Workspace Mode ═══════════════════════════════════════
        ws_card = self._card(self, "工作模式")
        frame = ctk.CTkFrame(ws_card, fg_color="transparent")
        frame.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))

        for icon_name, value, text in [
            ("server", "server", "Server Mode（服务器本机使用）"),
            ("terminal", "client", "Client Mode（运维电脑使用）"),
            (None, "ask", "启动时询问"),
        ]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row, text=text,
                variable=self._ws_var(), value=value,
                font=ctk.CTkFont(size=13),
                text_color=C["on_surface"],
                command=self._on_ws_change,
            ).pack(side="left")
            if icon_name:
                icon = load_icon(icon_name, size=16, color=C["primary"])
                ctk.CTkLabel(row, text="", image=icon).pack(side="left", padx=(PAD["sm"], 0))

        # ═══ Theme ════════════════════════════════════════════════
        theme_card = self._card(self, "外观")
        theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))

        ctk.CTkLabel(
            theme_row, text="主题", font=ctk.CTkFont(size=13),
            text_color=C["on_surface_variant"],
            width=80,
        ).pack(side="left")
        ctk.CTkLabel(
            theme_row, text="浅色",
            font=ctk.CTkFont(size=13),
            text_color=C["outline"],
        ).pack(side="left", padx=(PAD["sm"], 0))

        # ═══ Language ════════════════════════════════════════════
        lang_card = self._card(self, "语言")
        lang_row = ctk.CTkFrame(lang_card, fg_color="transparent")
        lang_row.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))
        ctk.CTkLabel(
            lang_row, text="界面语言", font=ctk.CTkFont(size=13),
            text_color=C["on_surface_variant"],
            width=80,
        ).pack(side="left")
        ctk.CTkLabel(
            lang_row, text="简体中文",
            font=ctk.CTkFont(size=13),
            text_color=C["outline"],
        ).pack(side="left")

        # ═══ About ═══════════════════════════════════════════════
        about = self._card(self, "关于")
        for label, val in [
            ("GP Server Manager", "v2.0 — Workspace"),
            ("Python", _sys.version.split()[0]),
            ("UI Framework", "CustomTkinter"),
        ]:
            row = ctk.CTkFrame(about, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=2)
            ctk.CTkLabel(
                row, text=label, font=ctk.CTkFont(size=12),
                text_color=C["on_surface"],
                width=120,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=val, font=ctk.CTkFont(size=12),
                text_color=C["outline"],
            ).pack(side="left")

        # ═══ Footer ══════════════════════════════════════════════
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=PAD["xl"], pady=(PAD["md"], PAD["lg"]))

        ctk.CTkButton(
            footer, text="← 返回首页", width=100,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["on_surface_variant"],
            hover_color=C["surface_variant"], corner_radius=8,
            command=self._go_back,
        ).pack(side="left")

        ctk.CTkButton(
            footer, text="💾 保存设置",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["primary"],
            text_color=C["on_primary"],
            hover_color=C["primary_hover"],
            corner_radius=8,
            command=self._save,
        ).pack(side="right")

        self._status = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11),
            text_color=C["outline"],
        )
        self._status.pack(pady=(0, PAD["md"]))

    def _ws_var(self) -> ctk.StringVar:
        if not hasattr(self, "_ws_var_inner"):
            mode = self._settings.workspace_mode
            self._ws_var_inner = ctk.StringVar(value=mode)
        return self._ws_var_inner

    def _on_ws_change(self) -> None:
        pass  # applied on save

    def _go_back(self) -> None:
        self._app._nav_to_home()

    def _save(self) -> None:
        self._settings.workspace_mode = self._ws_var().get()
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
