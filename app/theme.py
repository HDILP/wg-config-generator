"""Theme configuration for GP Server Manager.

Modern Windows / Material You inspired — light & dark with auto-switch support.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ThemeColors:
    # Primary
    primary: str = "#6750A4"       # Material You toned
    primary_hover: str = "#7C6DB5"
    primary_container: str = "#EADDFF"

    # Surface
    surface: str = "#FFFBFE"
    surface_variant: str = "#F3EDF7"
    surface_dark: str = "#1C1B1F"
    surface_variant_dark: str = "#2B2930"

    # On colors
    on_primary: str = "#FFFFFF"
    on_surface: str = "#1C1B1F"
    on_surface_variant: str = "#49454F"
    on_surface_dark: str = "#E6E1E5"
    on_surface_variant_dark: str = "#CAC4D0"

    # Status
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#B3261E"
    info: str = "#2196F3"

    # Borders
    outline: str = "#79747E"
    outline_variant: str = "#CAC4D0"
    outline_dark: str = "#938F99"
    outline_variant_dark: str = "#49454F"

    # Special
    sidebar_bg: str = "#F3EDF7"
    sidebar_bg_dark: str = "#2B2930"
    card_bg: str = "#FFFFFF"
    card_bg_dark: str = "#2B2930"

    # Score
    score_high: str = "#4CAF50"
    score_medium: str = "#FF9800"
    score_low: str = "#B3261E"


LIGHT: Dict[str, str] = {
    "primary": "#6750A4",
    "primary_hover": "#7C6DB5",
    "primary_container": "#EADDFF",
    "surface": "#FFFBFE",
    "surface_variant": "#F3EDF7",
    "on_primary": "#FFFFFF",
    "on_surface": "#1C1B1F",
    "on_surface_variant": "#49454F",
    "outline": "#79747E",
    "outline_variant": "#CAC4D0",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#B3261E",
}

DARK: Dict[str, str] = {
    "primary": "#D0BCFF",
    "primary_hover": "#B39DDB",
    "primary_container": "#4F378B",
    "surface": "#1C1B1F",
    "surface_variant": "#2B2930",
    "on_primary": "#381E72",
    "on_surface": "#E6E1E5",
    "on_surface_variant": "#CAC4D0",
    "outline": "#938F99",
    "outline_variant": "#49454F",
    "success": "#81C784",
    "warning": "#FFB74D",
    "error": "#F2B8B5",
}


def apply_theme(theme_mode: ThemeMode = ThemeMode.LIGHT) -> None:
    """Apply theme to customtkinter."""
    import customtkinter as ctk
    mode = "light" if theme_mode == ThemeMode.LIGHT else "dark"
    if theme_mode == ThemeMode.SYSTEM:
        mode = "system"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("green")  # base, overridden by styling below
