"""Empty state widget for GP Server Manager."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.theme import C, PAD, CR
from utils.icon_loader import load_icon


class EmptyState(ctk.CTkFrame):
    """A centered empty-state placeholder with icon, text, and optional action button.

    Usage:
        EmptyState(parent, icon="folder-open", text="还没有项目",
                   button_text="新建项目", on_click=self._app.show_new_project)
    """

    def __init__(
        self,
        master,
        icon: str = "folder-open",
        text: str = "",
        subtext: str = "",
        button_text: str = "",
        on_click: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        # Icon
        try:
            icon_img = load_icon(icon, size=48, color=C["accent2"])
            ctk.CTkLabel(self, text="", image=icon_img).pack(pady=(40, 12))
        except Exception:
            pass

        # Main text
        if text:
            ctk.CTkLabel(
                self, text=text,
                font=ctk.CTkFont(size=15),
                text_color=C["on_surface"],
            ).pack(pady=(0, 4))

        # Subtext
        if subtext:
            ctk.CTkLabel(
                self, text=subtext,
                font=ctk.CTkFont(size=12),
                text_color=C["outline"],
            ).pack(pady=(0, 16))

        # CTA button
        if button_text and on_click:
            ctk.CTkButton(
                self, text=button_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=on_click,
            ).pack(pady=(4, 0))
