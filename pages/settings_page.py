"""Settings page — global app settings."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.theme import ThemeMode

if TYPE_CHECKING:
    from app.app import GPServerManager


class SettingsPage(ctk.CTkFrame):
    """Global settings: theme, project directory, etc."""

    def __init__(self, master: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = master
        self._build()

    def _build(self) -> None:
        from core.project_manager import ProjectManager

        ctk.CTkLabel(self, text="设置", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(20, 16))

        # Theme
        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="外观", font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        theme_row = ctk.CTkFrame(card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(theme_row, text="主题", font=ctk.CTkFont(size=13),
                     width=80).pack(side="left")
        theme_var = ctk.StringVar(value="light")
        ctk.CTkOptionMenu(theme_row, values=["浅色", "深色", "跟随系统"],
                          variable=theme_var,
                          font=ctk.CTkFont(size=12),
                          command=self._change_theme,
                          ).pack(side="left", padx=(8, 0))

        # Project directory
        ctk.CTkLabel(card, text="项目存储", font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 2))

        dir_row = ctk.CTkFrame(card, fg_color="transparent")
        dir_row.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(dir_row, text="路径", font=ctk.CTkFont(size=13),
                     width=80).pack(side="left")
        path_label = ctk.CTkLabel(
            dir_row, text=str(ProjectManager.PROJECTS_DIR.resolve()),
            font=ctk.CTkFont(size=12), text_color="#79747E", anchor="w",
        )
        path_label.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # About
        sep = ctk.CTkLabel(self, text="─" * 40, text_color="#79747E",
                            font=ctk.CTkFont(size=10))
        sep.pack(pady=(8, 8))

        about = ctk.CTkFrame(self, corner_radius=12)
        about.pack(fill="x", padx=24)

        ctk.CTkLabel(about, text="关于", font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        import sys as _sys
        for label, val in [
            ("GP Server Manager", "v1.0.0"),
            ("Python", _sys.version.split()[0]),
            ("UI Framework", "CustomTkinter"),
        ]:
            row = ctk.CTkFrame(about, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         width=120).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         text_color="#79747E").pack(side="left")

        # Back
        ctk.CTkButton(self, text="← 返回首页", width=110,
                       font=ctk.CTkFont(size=12),
                       command=self._app.show_home,
                       ).pack(anchor="w", padx=24, pady=(16, 8))

    def _change_theme(self, choice: str) -> None:
        mapping = {"浅色": "light", "深色": "dark", "跟随系统": "system"}
        mode = mapping.get(choice, "light")
        ctk.set_appearance_mode(mode)
