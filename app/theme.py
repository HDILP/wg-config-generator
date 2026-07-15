"""Theme configuration for GP Server Manager.

Material Design 3 color system — seeded from #6750A4.
Light & dark themes with semantic tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass(frozen=True)
class ColorTokens:
    """M3 semantic color tokens."""
    # Primary
    primary: str
    primary_fixed: str
    primary_fixed_dim: str
    on_primary: str
    primary_container: str
    on_primary_container: str

    # Secondary
    secondary: str
    secondary_container: str
    on_secondary: str
    on_secondary_container: str

    # Tertiary
    tertiary: str
    tertiary_container: str
    on_tertiary: str
    on_tertiary_container: str

    # Error
    error: str
    error_container: str
    on_error: str
    on_error_container: str

    # Surface
    surface: str
    surface_dim: str
    surface_bright: str
    surface_container_lowest: str
    surface_container_low: str
    surface_container: str
    surface_container_high: str
    surface_container_highest: str
    on_surface: str
    on_surface_variant: str
    outline: str
    outline_variant: str
    shadow: str
    scrim: str

    # Inverse
    inverse_surface: str
    inverse_on_surface: str
    inverse_primary: str


# ── Light theme (seed #6750A4) ──────────────────────────────────────
LIGHT: ColorTokens = ColorTokens(
    primary="#6750A4",
    primary_fixed="#EADDFF",
    primary_fixed_dim="#B39DDB",
    on_primary="#FFFFFF",
    primary_container="#EADDFF",
    on_primary_container="#21005D",

    secondary="#775984",
    secondary_container="#F3DEFF",
    on_secondary="#FFFFFF",
    on_secondary_container="#2D143B",

    tertiary="#6B5D2F",
    tertiary_container="#F5DFAD",
    on_tertiary="#FFFFFF",
    on_tertiary_container="#231900",

    error="#B3261E",
    error_container="#F9DEDC",
    on_error="#FFFFFF",
    on_error_container="#410E0B",

    surface="#FFFBFE",
    surface_dim="#DED8E1",
    surface_bright="#FFFBFE",
    surface_container_lowest="#FFFFFF",
    surface_container_low="#F7F2FA",
    surface_container="#F3EDF7",
    surface_container_high="#ECE6F0",
    surface_container_highest="#E6E0E9",
    on_surface="#1C1B1F",
    on_surface_variant="#49454F",
    outline="#79747E",
    outline_variant="#CAC4D0",
    shadow="#000000",
    scrim="#000000",

    inverse_surface="#313033",
    inverse_on_surface="#F4EFF4",
    inverse_primary="#D0BCFF",
)

# ── Dark theme (seed #D0BCFF) ───────────────────────────────────────
DARK: ColorTokens = ColorTokens(
    primary="#D0BCFF",
    primary_fixed="#EADDFF",
    primary_fixed_dim="#B39DDB",
    on_primary="#381E72",
    primary_container="#4F378B",
    on_primary_container="#EADDFF",

    secondary="#CCC2DC",
    secondary_container="#442D56",
    on_secondary="#442D56",
    on_secondary_container="#F3DEFF",

    tertiary="#D8C38E",
    tertiary_container="#524419",
    on_tertiary="#3B2F05",
    on_tertiary_container="#F5DFAD",

    error="#F2B8B5",
    error_container="#8C1D18",
    on_error="#601410",
    on_error_container="#F9DEDC",

    surface="#141218",
    surface_dim="#2B2930",
    surface_bright="#514F57",
    surface_container_lowest="#100F14",
    surface_container_low="#1C1B1F",
    surface_container="#211F26",
    surface_container_high="#2B2930",
    surface_container_highest="#36343B",
    on_surface="#E6E1E5",
    on_surface_variant="#CAC4D0",
    outline="#938F99",
    outline_variant="#49454F",
    shadow="#000000",
    scrim="#000000",

    inverse_surface="#E6E1E5",
    inverse_on_surface="#313033",
    inverse_primary="#6750A4",
)


def get_colors(mode: str = "light") -> ColorTokens:
    """Return the color tokens for the given appearance mode."""
    return LIGHT if mode == "light" else DARK


def apply_theme(theme_mode: ThemeMode = ThemeMode.LIGHT) -> None:
    """Apply theme to customtkinter."""
    import customtkinter as ctk
    mode = "light" if theme_mode == ThemeMode.LIGHT else "dark"
    if theme_mode == ThemeMode.SYSTEM:
        mode = "system"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("green")  # base, overridden by styling below
