"""Card components for GP Server Manager.

Simple, composable card containers with consistent padding and styling.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Optional


def Card(master, title: str = "", **kwargs) -> ctk.CTkFrame:
    """Create a styled card frame with optional title.

    Args:
        master: Parent widget.
        title: Optional card title displayed at top.
        **kwargs: Passed to CTkFrame constructor.

    Returns:
        A CTkFrame ready for content packing.
    """
    corner_radius = kwargs.pop("corner_radius", 12)
    fg_color = kwargs.pop("fg_color", None)  # transparent by default

    frame = ctk.CTkFrame(master, corner_radius=corner_radius, fg_color=fg_color, **kwargs)

    if title:
        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 8))

    return frame


def SectionHeader(master, text: str) -> None:
    """Add a section divider line + label inside a parent frame."""
    ctk.CTkLabel(master, text="", height=1, fg_color="#CAC4D0").pack(
        fill="x", padx=0, pady=(16, 4)
    )
    ctk.CTkLabel(
        master,
        text=text,
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="#79747E",
        anchor="w",
    ).pack(fill="x", padx=0, pady=(0, 8))
