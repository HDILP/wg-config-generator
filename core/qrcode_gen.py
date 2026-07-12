"""QR code generation for WireGuard client configs."""
from __future__ import annotations

import base64
from pathlib import Path

from core.templates import CLIENT_CONF


def _wg_uri(config_text: str) -> str:
    """Encode a client.conf as a wireguard:// URI."""
    encoded = base64.b64encode(config_text.encode()).decode()
    return f"wireguard://{encoded}"


def generate_qr_code(text: str, save_path: Path, size: int = 400) -> None:
    """Generate a QR code PNG from text.

    Falls back to a simple SVG if qrcode+pillow not installed.
    """
    try:
        import qrcode
        from qrcode.image.pil import PilImage

        qr = qrcode.QRCode(box_size=size // 25, border=2)
        qr.add_data(text)
        img = qr.make_image(PilImage, fill_color="black", back_color="white")
        img.save(save_path)
    except ImportError:
        _fallback_svg_qr(text, save_path)


def _fallback_svg_qr(text: str, save_path: Path) -> None:
    """Minimal SVG QR fallback if Python qrcode lib not available."""
    # ponytail: naive placeholder — real QR requires qrcode + pillow
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="white"/>
  <text x="100" y="100" text-anchor="middle" font-size="12"
        font-family="monospace" fill="black">
    QR: Install qrcode[pil] to render
  </text>
  <text x="100" y="130" text-anchor="middle" font-size="8"
        font-family="monospace" fill="#666">
    {text[:50]}...
  </text>
</svg>"""
    save_path.write_text(svg, encoding="utf-8")


def client_conf_to_qr(
    client_name: str,
    private_key: str,
    address: str,
    server_public_key: str,
    endpoint: str,
    allowed_ips: str,
    dns: str = "1.1.1.1",
    persistent_keepalive: int = 25,
    save_path: Path | None = None,
) -> str:
    """Generate a client.conf string and optionally save its QR code.

    Returns the config text.
    """
    config = CLIENT_CONF.format(
        private_key=private_key,
        address=address,
        dns=dns,
        server_public_key=server_public_key,
        endpoint=endpoint,
        allowed_ips=allowed_ips,
        persistent_keepalive=persistent_keepalive,
    )
    if save_path:
        uri = _wg_uri(config)
        generate_qr_code(uri, save_path)
    return config
