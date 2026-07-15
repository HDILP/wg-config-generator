"""Button components for GP Server Manager.

Semantic button factory: PrimaryButton, SecondaryButton, DangerButton.
Colors sourced from theme.py tokens.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional

from app.theme import get_colors


def PrimaryButton(master, text="", command=None, **kwargs):
    return _ActionButton(master, text=text, style="primary", command=command, **kwargs)


def SecondaryButton(master, text="", command=None, **kwargs):
    return _ActionButton(master, text=text, style="secondary", command=command, **kwargs)


def DangerButton(master, text="", command=None, **kwargs):
    return _ActionButton(master, text=text, style="danger", command=command, **kwargs)


def _ActionButton(master, text="", style="primary", command=None, **kwargs):
    """Factory function for semantic buttons.

    Args:
        master: Parent widget.
        text: Button label.
        style: "primary", "secondary", or "danger".
        command: Click callback.
        **kwargs: Passed to CTkButton.
    """
    colors = get_colors(ctk.get_appearance_mode())
    fg_map = {
        "primary": colors.primary,
        "secondary": "transparent",
        "danger": colors.error,
    }
    txt_map = {
        "primary": colors.on_primary,
        "secondary": colors.secondary,
        "danger": colors.on_error,
    }
    hover_map = {
        "primary": colors.on_primary_container,
        "secondary": colors.surface_container,
        "danger": "#D32F2F",
    }

    fg_color = fg_map.get(style, fg_map["primary"])
    txt_color = txt_map.get(style, txt_map["primary"])
    hover_color = hover_map.get(style, hover_map["primary"])

    height = kwargs.pop("height", 32)
    font = kwargs.pop("font", ctk.CTkFont(size=13))
    if style == "primary":
        font = ctk.CTkFont(size=13, weight="bold")

    btn = ctk.CTkButton(
        master,
        text=text,
        font=font,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=txt_color,
        height=height,
        corner_radius=8,
        command=command,
        **kwargs,
    )
    return btn
