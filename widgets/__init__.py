"""Reusable UI widgets for GP Server Manager."""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, List, Optional


class SidebarButton(ctk.CTkButton):
    """A nav button with active state indicator."""

    def __init__(
        self,
        master,
        text: str,
        icon: str = "",
        active: bool = False,
        command: Optional[Callable] = None,
        **kwargs,
    ):
        display = f"{icon}  {text}" if icon else text
        fg = "#EADDFF" if active else "transparent"
        txt = "#1C1B1F" if active else "#49454F"
        hover = "#D0BCFF" if active else "#F3EDF7"

        super().__init__(
            master,
            text=display,
            font=ctk.CTkFont(size=13),
            fg_color=fg,
            text_color=txt,
            hover_color=hover,
            anchor="w",
            corner_radius=8,
            height=36,
            command=command,
            **kwargs,
        )


class SectionLabel(ctk.CTkLabel):
    """A section header label for sidebar sections."""

    def __init__(self, master, text: str, **kwargs):
        super().__init__(
            master,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#79747E",
            anchor="w",
            **kwargs,
        )


class StatusIndicator(ctk.CTkFrame):
    """A small colored dot + label for status display."""

    def __init__(self, master, label: str, status: str = "unknown", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._dot = ctk.CTkLabel(self, text="●", font=ctk.CTkFont(size=14))
        self._dot.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=12)).pack(side="left")
        self.set_status(status)

    def set_status(self, status: str) -> None:
        colors = {"ok": "#4CAF50", "error": "#B3261E", "warning": "#FF9800", "unknown": "#9E9E9E"}
        self._dot.configure(text_color=colors.get(status, "#9E9E9E"))


class SecurityScoreWidget(ctk.CTkFrame):
    """Security score circle with item list."""

    def __init__(
        self,
        master,
        score: int = 95,
        items: Optional[List] = None,
        **kwargs,
    ):
        super().__init__(master, corner_radius=16, **kwargs)
        self._score = score
        self._items = items or []

        # Score circle
        score_frame = ctk.CTkFrame(self, fg_color="transparent")
        score_frame.pack(pady=(16, 12))

        color = "#4CAF50" if score >= 80 else "#FF9800" if score >= 50 else "#B3261E"
        ctk.CTkLabel(
            score_frame,
            text=str(score),
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color=color,
        ).pack()
        ctk.CTkLabel(
            score_frame,
            text="/ 100",
            font=ctk.CTkFont(size=14),
            text_color="#79747E",
        ).pack()

        # Items
        item_frame = ctk.CTkFrame(self, fg_color="transparent")
        item_frame.pack(fill="x", padx=16, pady=(0, 12))
        for item in self._items:
            row = ctk.CTkFrame(item_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            icon = "✓" if item.get("ok") else "✗"
            c = "#4CAF50" if item.get("ok") else "#B3261E"
            ctk.CTkLabel(row, text=icon, text_color=c, font=ctk.CTkFont(size=13),
                         width=20).pack(side="left")
            ctk.CTkLabel(row, text=item.get("label", ""), font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", fill="x", expand=True)


class CardFrame(ctk.CTkFrame):
    """A rounded card container."""

    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(master, corner_radius=12, **kwargs)
        if title:
            ctk.CTkLabel(
                self, text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 8))
