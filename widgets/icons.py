"""Icon rendering for GP Server Manager.

Converts Lucide SVG icon names to CTkImage using svgelements + Pillow.
All icons rendered at theme-aware stroke color.
"""
from __future__ import annotations

import tempfile
import os
from typing import Dict, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

# Lazy import to avoid startup cost
_lucide_cache: Dict[str, ctk.CTkImage] = {}


def _render_svg_to_image(svg_path_data: str, size: int = 20,
                          stroke_color: str = "#49454F",
                          stroke_width: float = 1.8,
                          scale: float = 1.0) -> ctk.CTkImage:
    """Render a single Lucide SVG path to a CTkImage.

    Args:
        svg_path_data: The `d` attribute of a Lucide <path> element.
        size: Base icon size in pixels.
        stroke_color: Hex color for the icon stroke.
        stroke_width: Stroke width in SVG units.
        scale: DPI scale factor (1.0 for normal, 2.0 for HiDPI).
    """
    import svgelements as se

    viewBox = "0 0 24 24"

    # Build a minimal SVG string
    svg_str = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewBox}" '
        f'width="24" height="24">'
        f'<path d="{svg_path_data}" fill="none" stroke="{stroke_color}" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        f'</svg>'
    )

    # svgelements 1.9.6: SVG.parse() takes a file path, not a string.
    # Write to temp file, parse, then delete.
    fd, tmp_path = tempfile.mkstemp(suffix=".svg")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(svg_str)
        doc = se.SVG.parse(tmp_path)
        doc.reify()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Collect all Path objects by iterating the doc
    paths: list[se.Path] = []
    for obj in doc:
        if isinstance(obj, se.Path):
            paths.append(obj)

    if not paths:
        # Fallback: blank image
        img = Image.new("RGBA", (int(size * scale), int(size * scale)), (0, 0, 0, 0))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(int(size * scale), int(size * scale)))

    # Get bounding box (union of all paths)
    bbox = paths[0].bbox() if paths else (0, 0, 24, 24)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    if bw == 0 or bh == 0:
        bw, bh = 24, 24

    # Scale to desired size with padding
    pad = 2
    img_size = int((size + pad * 2) * scale)
    img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate transform
    scale_x = size / bw if bw else 1
    scale_y = size / bh if bh else 1
    s = min(scale_x, scale_y)
    ox = (size - bw * s) / 2
    oy = (size - bh * s) / 2

    # Draw each path element
    for elem in paths:
        points: list[tuple[float, float]] = []
        for cmd in elem:
            cmd_type = type(cmd).__name__
            if cmd_type == "Move":
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "Line":
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "HLine":
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "VLine":
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "CubicBezier":
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "Arc":
                # Approximate arc with line segment from start to end
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type in ("QuadraticBezier", "SmoothQuadratic"):
                points.append((cmd.end.x - bbox[0], cmd.end.y - bbox[1]))
            elif cmd_type == "Close":
                if points:
                    draw.line(
                        [(p[0] * s + ox, p[1] * s + oy) for p in points],
                        fill=stroke_color, width=max(1, int(stroke_width * s)),
                    )
                points = []
                continue

        if points and len(points) >= 2:
            draw.line(
                [(p[0] * s + ox, p[1] * s + oy) for p in points],
                fill=stroke_color, width=max(1, int(stroke_width * s)),
                joint="curve",
            )
        elif points:
            draw.point(
                [(points[0][0] * s + ox, points[0][1] * s + oy)],
                fill=stroke_color,
            )

    return ctk.CTkImage(light_image=img, dark_image=img, size=(img_size, img_size))


# ── Lucide icon path data (subset used by GP Server Manager) ──────────
# Copied from lucide-icons SVG paths. Each entry: (name, path_d)
_ICON_PATHS: Dict[str, str] = {
    "activity": "M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 6.36a1 1 0 0 1-1.88 0l-1.58-4.76a2 2 0 0 0-1.93-1.46h-.96a2 2 0 0 0-1.93 1.46l-1.58 4.76a1 1 0 0 1-1.88 0l-2.35-6.36A2 2 0 0 0 4.48 12H2",
    "database": "M12 8c-3.87 0-7 1.34-7 3s3.13 3 7 3s7 -1.34 7 -3s-3.13 -3 -7 -3zm0 -6c-3.87 0 -7 1.34 -7 3s3.13 3 7 3s7 -1.34 7 -3s-3.13 -3 -7 -3zm0 12c-4.42 0 -8 1.34 -8 3s3.58 3 8 3s8 -1.34 8 -3s-3.58 -3 -8 -3z",
    "shield-check": "M20 13c0 5-3.5 8.5-8 10.5C7.5 21.5 4 18 4 13V6l8-3l8 3ZM9.5 12.5l1.5 1.5L14.5 9.5",
    "shield-alert": "M19.7 14.6l-1.7 9.6a2 2 0 0 1-1.9 1.5H7.9a2 2 0 0 1-1.9-1.5l-1.7-9.6A8 8 0 0 1 12 3.5a8 8 0 0 1 7.7 11.1zM12 9v4M12 15h.01",
    "hard-drive-upload": "M12 14v4M10 18h4M5.5 6.5a2.5 2.5 0 0 1 5 0v1a2.5 2.5 0 0 1-5 0v-1zM19.5 6.5a2.5 2.5 0 0 1-5 0v1a2.5 2.5 0 0 1 5 0v-1zM12 6.5v7M3 13h18a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2z",
    "settings": "M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M19 12a7 7 0 11-14 0a7 7 0 0114 0z",
    "cpu": "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 0v12m16-12v12M8 8h.01M12 8h.01M16 8h.01M8 12h.01M12 12h.01M16 12h.01M8 16h.01M12 16h.01M16 16h.01",
    "folder-tree": "M5.5 8.5L9 12L5.5 15.5L2 12ZM12 2L16.27 3.27Q17.5 3.77 18.5 4.77T20 8L20.5 16H4L2 8Q2 5.5 3.75 3.75T8 2H12Z",
    "users": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 11a4 4 0 1 0-8 0a4 4 0 0 0 8 0M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
    "clipboard-list": "M16 14V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM16 14l2 2l4-4M16 8h4M16 12h4M9 16h1",
    "menu": "M4 6h16M4 12h16M4 18h16",
    "x": "M18 6L6 18M6 6l12 12",
    "chevron-left": "M15 18l-6-6l6-6",
    "chevron-right": "M9 18l6-6l-6-6",
    "check": "M20 6L9 17l-5-5",
    "alert-circle": "M12 22c5.52 0 10-4.48 10-10S17.52 2 12 2S2 6.48 2 12s4.48 10 10 10zM12 8v4M12 16h.01",
    "info": "M12 22c5.52 0 10-4.48 10-10S17.52 2 12 2S2 6.48 2 12s4.48 10 10 10zM12 16v-4M12 8h.01",
    "refresh-cw": "M3 12a9 9 0 0 1 9-9a9 9 0 0 1 6.36 2.64L21 8M21 12a9 9 0 0 1-9 9a9 9 0 0 1-6.36-2.64L3 16M12 3v9M12 12l3-3",
    "download": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5l5-5M12 15V3",
    "upload": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5l-5 5M12 3v12",
    "trash-2": "M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6",
    "copy": "M20 9h-1a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2zM17 6H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-1",
    "eye": "M2 12s3-7 10-7s10 7 10 7s-3 7-10 7s-10-7-10-7zM12 5a7 7 0 0 0-7 7a7 7 0 0 0 7 7a7 7 0 0 0 7-7a7 7 0 0 0-7-7z",
    "eye-off": "M10.73 4.27L4.27 10.73A7 7 0 0 0 2 12s3 7 10 7a7 7 0 0 0 6.73-4.27M13.27 13.27L16.73 9.73A7 7 0 0 0 12 5a7 7 0 0 0-3.73 1.07M10 12a2 2 0 1 1 0-4a2 2 0 0 1 0 4z",
    "plus": "M12 5v14M5 12h14",
    "minus": "M5 12h14",
    "save": "M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2zM17 21v-8H7v8M7 3v5h8",
    "power": "M18.36 6.64a9 9 0 1 1-12.73 0M12 2v10",
    "server": "M6 1H18a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2zM6 17H18a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2zM4 6h16M4 18h16",
    "lock": "M19 11H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2zM7 11V7a5 5 0 0 1 10 0v4",
    "zap": "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    "key": "M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4",
    "qr-code": "M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h2v2h-2z",
    "file-text": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
    "monitor": "M3 5v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z M3 10h18",
    "wifi": "M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01",
}


def get_icon(name: str, size: int = 20,
             color: Optional[str] = None,
             scale: float = 1.0) -> Optional[ctk.CTkImage]:
    """Get a cached Lucide icon as CTkImage.

    Args:
        name: Lucide icon name (e.g. "activity", "database").
        size: Display size in pixels.
        color: Stroke color (hex). Defaults to on_surface_variant.
        scale: DPI scale (1.0 or 2.0).

    Returns:
        CTkImage instance, or None if icon not found.
    """
    if name not in _ICON_PATHS:
        return None

    # Determine color based on appearance mode
    if color is None:
        mode = ctk.get_appearance_mode()
        color = "#49454F" if mode == "light" else "#CAC4D0"

    cache_key = f"{name}:{size}:{color}:{scale}"
    if cache_key in _lucide_cache:
        return _lucide_cache[cache_key]

    path_d = _ICON_PATHS[name]
    img = _render_svg_to_image(path_d, size=size, stroke_color=color, scale=scale)
    _lucide_cache[cache_key] = img
    return img


def get_sidebar_icon(name: str) -> Optional[ctk.CTkImage]:
    """Get icon for sidebar navigation (18px)."""
    return get_icon(name, size=18)


def get_icon_button(name: str) -> Optional[ctk.CTkImage]:
    """Get icon for buttons (16px)."""
    return get_icon(name, size=16)


def get_large_icon(name: str) -> Optional[ctk.CTkImage]:
    """Get icon for large displays (24px)."""
    return get_icon(name, size=24)
