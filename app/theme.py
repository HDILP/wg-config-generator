"""Theme configuration for GP Server Manager.

Light mode only — color tokens and design constants.
"""
from __future__ import annotations

from typing import Dict


# Design tokens
C = {
    "primary": "#6750A4",
    "primary_hover": "#7C6DB5",
    "primary_container": "#EADDFF",
    "accent": "#ffaab2",
    "accent_hover": "#ffccd5",
    "accent2": "#A5D8FF",
    "accent2_hover": "#ccebff",
    "surface": "#FFFBFE",
    "surface_variant": "#F3EDF7",
    "card_bg": "#FFF8FA",
    "container_bg": "#FFF8FA",
    "on_primary": "#FFFFFF",
    "on_surface": "#1C1B1F",
    "on_surface_variant": "#49454F",
    "outline": "#79747E",
    "outline_variant": "#CAC4D0",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#B3261E",
}

PAD = {
    "sm": 4,
    "md": 8,
    "lg": 16,
    "xl": 24,
}

CR = 12  # default corner_radius
CR_SM = 8
CR_LG = 20


def apply_theme() -> None:
    """Apply light theme to customtkinter."""
    import customtkinter as ctk
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
