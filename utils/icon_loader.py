"""Load Lucide SVG icons as CTkImage objects.

Usage:
    from utils.icon_loader import load_icon
    icon = load_icon("layout-dashboard", size=24, color="#6750A4")
    button.configure(image=icon)

Icons: layout-dashboard, database, lock, shield, hard-drive, settings,
       folder-open, file-text, refresh-cw, save, plus, server, users,
       activity, chevron-down, chevron-up, search, home, terminal
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw
from svg.path import parse_path as parse_svg_path

_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
_CACHE: dict[str, ctk.CTkImage] = {}


def clear_cache() -> None:
    """Clear the icon cache (call when Tk root is destroyed)."""
    _CACHE.clear()


def _decompose_cubic(p0, p1, p2, p3, steps: int = 12):
    """Cubic bezier to line segments."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * p0.real + 3 * mt**2 * t * p1.real + 3 * mt * t**2 * p2.real + t**3 * p3.real
        y = mt**3 * p0.imag + 3 * mt**2 * t * p1.imag + 3 * mt * t**2 * p2.imag + t**3 * p3.imag
        pts.append((x, y))
    return pts


def _decompose_quadratic(p0, p1, p2, steps: int = 8):
    """Quadratic bezier to line segments."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**2 * p0.real + 2 * mt * t * p1.real + t**2 * p2.real
        y = mt**2 * p0.imag + 2 * mt * t * p1.imag + t**2 * p2.imag
        pts.append((x, y))
    return pts


def _decompose_arc(p0, rx, ry, x_rot, large_flag, sweep_flag, p1, steps: int = 16):
    """SVG arc to line segments (simplified)."""
    from math import cos, sin, radians, degrees, atan2, sqrt, pi

    # Convert to endpoint parameterization
    x1, y1 = p0.real, p0.imag
    x2, y1_end = p1.real, p1.imag

    if rx == 0 or ry == 0:
        return [(x1, y1), (x2, y1_end)]

    cos_r = cos(radians(x_rot))
    sin_r = sin(radians(x_rot))

    # Step 1: compute (x1', y1')
    dx = (x1 - x2) / 2
    dy = (y1 - y1_end) / 2
    x1p = cos_r * dx + sin_r * dy
    y1p = -sin_r * dx + cos_r * dy

    # Ensure radii are large enough
    r = max(rx, ry)
    lam = (x1p**2) / (rx**2) + (y1p**2) / (ry**2)
    if lam > 1:
        rx = math.sqrt(lam) * rx
        ry = math.sqrt(lam) * ry

    # Step 2: compute (cx', cy')
    s = math.sqrt(max(0, (rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2) / (rx**2 * y1p**2 + ry**2 * x1p**2)))
    s = -s if large_flag == sweep_flag else s
    cxp = s * rx * y1p / ry
    cyp = -s * ry * x1p / rx

    # Step 3: compute (cx, cy)
    cx = cos_r * cxp - sin_r * cyp + (x1 + x2) / 2
    cy = sin_r * cxp + cos_r * cyp + (y1 + y1_end) / 2

    # Step 4: compute start/end angles
    start_angle = degrees(atan2((y1p - cyp) / ry, (x1p - cxp) / rx))
    end_angle = degrees(atan2((-y1p - cyp) / ry, (-x1p - cxp) / rx))

    # Determine sweep
    if sweep_flag and end_angle < start_angle:
        end_angle += 360
    elif not sweep_flag and end_angle > start_angle:
        end_angle -= 360

    pts = []
    angle_step = (end_angle - start_angle) / steps
    for i in range(steps + 1):
        theta = start_angle + i * angle_step
        cost = cos(radians(theta))
        sint = sin(radians(theta))
        x = cx + rx * cos_r * cost - ry * sin_r * sint
        y = cy + rx * sin_r * cost + ry * cos_r * sint
        pts.append((x, y))
    return pts


def _svg_to_pil(svg_path: Path, size: int, color: str) -> Image.Image:
    """Parse an SVG file and render to a PIL Image."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Get viewBox dimensions for scaling
    vb = root.get("viewBox", "0 0 24 24")
    parts = [float(x) for x in vb.split()]
    vx, vy, vw, vh = parts if len(parts) == 4 else (0, 0, 24, 24)

    scale = size / max(vw, vh)
    offset_x = (size - vw * scale) / 2
    offset_y = (size - vh * scale) / 2

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    stroke_width = float(root.get("stroke-width", "2"))
    line_width = max(1, int(stroke_width * scale))

    def tf(x, y):
        return (offset_x + (x - vx) * scale, offset_y + (y - vy) * scale)

    def draw_path(path_elem):
        d = path_elem.get("d", "")
        fill = path_elem.get("fill", "none")
        stroke = path_elem.get("stroke", color)

        # Skip pure-filled shapes (like the house icon's roof fill)
        if stroke in ("none", "") and fill == "none":
            return

        parsed = parse_svg_path(d)

        segments = []
        raw_pts: list[tuple[float, float]] = []

        for seg in parsed:
            tag = type(seg).__name__
            if tag == "Move":
                pt = tf(seg.end.real, seg.end.imag)
                if raw_pts and len(raw_pts) > 1:
                    segments.append(raw_pts)
                raw_pts = [pt]
            elif tag == "Line":
                raw_pts.append(tf(seg.end.real, seg.end.imag))
            elif tag == "Close":
                if raw_pts and len(raw_pts) > 1:
                    segments.append(raw_pts)
                raw_pts = []
            elif tag == "CubicBezier":
                pts = _decompose_cubic(
                    seg.start, seg.control1, seg.control2, seg.end
                )
                for pt in pts:
                    raw_pts.append(tf(pt[0], pt[1]))
            elif tag == "QuadraticBezier":
                pts = _decompose_quadratic(
                    seg.start, seg.control1, seg.end
                )
                for pt in pts:
                    raw_pts.append(tf(pt[0], pt[1]))
            elif tag == "Arc":
                pts = _decompose_arc(
                    seg.start, seg.radius.real, seg.radius.imag,
                    seg.rotation, seg.arc, seg.sweep, seg.end
                )
                for pt in pts:
                    raw_pts.append(tf(pt[0], pt[1]))

        if raw_pts and len(raw_pts) > 1:
            segments.append(raw_pts)

        for segment in segments:
            if len(segment) < 2:
                continue
            # Determine if this segment should be filled or stroked
            drawing_color = stroke if stroke not in ("none", "") else color
            if fill not in ("none", ""):
                # Filled polygon
                draw.polygon(segment, fill=fill, outline=None)
            # Draw the stroke lines
            for i in range(len(segment) - 1):
                draw.line([segment[i], segment[i + 1]], fill=drawing_color, width=line_width)

    def draw_polyline(elem):
        points_str = elem.get("points", "")
        if not points_str:
            return
        pairs = points_str.strip().replace(",", " ").split()
        pts = [(float(pairs[i]), float(pairs[i + 1])) for i in range(0, len(pairs), 2)]
        scaled = [tf(x, y) for x, y in pts]
        stroke = elem.get("stroke", color)
        for i in range(len(scaled) - 1):
            draw.line([scaled[i], scaled[i + 1]], fill=stroke, width=line_width)

    def draw_circle(elem):
        cx = float(elem.get("cx", 0))
        cy = float(elem.get("cy", 0))
        r = float(elem.get("r", 0))
        stroke = elem.get("stroke", color)
        fill = elem.get("fill", "none")
        x, y = tf(cx - r, cy - r)
        d = r * 2 * scale
        if fill not in ("none", ""):
            draw.ellipse([x, y, x + d, y + d], fill=fill, outline=None)
        draw.ellipse([x, y, x + d, y + d], outline=stroke, width=line_width)

    def draw_rect(elem):
        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        w = float(elem.get("width", 0))
        h = float(elem.get("height", 0))
        rx = float(elem.get("rx", 0))
        stroke = elem.get("stroke", color)
        fill = elem.get("fill", "none")
        p1 = tf(x, y)
        p2 = tf(x + w, y + h)
        if fill not in ("none", ""):
            draw.rectangle([p1, p2], fill=fill, outline=None)
        draw.rectangle([p1, p2], outline=stroke, width=line_width)

    def draw_line(elem):
        x1 = float(elem.get("x1", 0))
        y1 = float(elem.get("y1", 0))
        x2 = float(elem.get("x2", 0))
        y2 = float(elem.get("y2", 0))
        stroke = elem.get("stroke", color)
        draw.line([tf(x1, y1), tf(x2, y2)], fill=stroke, width=line_width)

    ns = {"svg": "http://www.w3.org/2000/svg"}
    for child in root:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "path":
            draw_path(child)
        elif tag == "polyline":
            draw_polyline(child)
        elif tag == "circle":
            draw_circle(child)
        elif tag == "rect":
            draw_rect(child)
        elif tag == "line":
            draw_line(child)
        elif tag == "polygon":
            # Treat polygons as filled polylines
            points_str = child.get("points", "")
            if not points_str:
                continue
            pairs = points_str.strip().replace(",", " ").split()
            pts = [(float(pairs[i]), float(pairs[i + 1])) for i in range(0, len(pairs), 2)]
            scaled = [tf(x, y) for x, y in pts]
            fill = child.get("fill", "none")
            stroke = child.get("stroke", "none")
            if fill not in ("none", ""):
                draw.polygon(scaled, fill=fill)
            elif stroke not in ("none", ""):
                draw.polygon(scaled, outline=stroke, width=line_width)

    return img


def load_icon(name: str, size: int = 24, color: str = "#6750A4") -> ctk.CTkImage:
    """Load an icon by name as a CTkImage.

    Icons are cached after first load. Change color by passing a new value.
    """
    cache_key = f"{name}:{size}:{color}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    svg_path = _ICON_DIR / f"{name}.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"Icon '{name}' not found at {svg_path}")

    pil_img = _svg_to_pil(svg_path, size, color)
    ctkim = ctk.CTkImage(pil_img, pil_img, size=(size, size))
    _CACHE[cache_key] = ctkim
    return ctkim
