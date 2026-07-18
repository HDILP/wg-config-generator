"""WireGuard service — interact with running wg instances via wg.exe show."""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.wg_keygen import KeyGenError, _wg_path  # noqa: PLC2701 — internal coupling


@dataclass
class WGPeerInfo:
    public_key: str
    endpoint: str = ""
    allowed_ips: str = ""
    latest_handshake: str = ""
    transfer_rx: str = ""
    transfer_tx: str = ""
    persistent_keepalive: str = ""


@dataclass
class WGDeviceInfo:
    interface: str = ""
    private_key: str = ""
    public_key: str = ""
    listen_port: int = 0
    fwmark: str = ""
    peers: List[WGPeerInfo] = field(default_factory=list)


def _run_wg(args: List[str], timeout: int = 10) -> str:
    wg = _wg_path()
    try:
        r = subprocess.run(
            [wg, *args], capture_output=True, check=True, timeout=timeout
        )
        return r.stdout.decode().strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        raise KeyGenError(f"wg {' '.join(args)} failed: {exc}") from exc


def wg_show(interface: str = "") -> WGDeviceInfo:
    """Parse `wg show [interface]` dump into structured data."""
    raw = _run_wg(["show", interface] if interface else ["show"])
    info = WGDeviceInfo()
    current_peer: Optional[WGPeerInfo] = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # ponytail: naive dump parser, fine for wg show output
        if line.startswith("interface:"):
            info.interface = line.split(":", 1)[1].strip()
        elif line.startswith("private key:"):
            info.private_key = line.split(":", 1)[1].strip()
        elif line.startswith("public key:"):
            info.public_key = line.split(":", 1)[1].strip()
        elif line.startswith("listening port:"):
            try:
                info.listen_port = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("fwmark:"):
            info.fwmark = line.split(":", 1)[1].strip()
        elif line.startswith("peer:"):
            current_peer = WGPeerInfo(
                public_key=line.split(":", 1)[1].strip()
            )
            info.peers.append(current_peer)
        elif current_peer:
            if line.startswith("endpoint:"):
                current_peer.endpoint = line.split(":", 1)[1].strip()
            elif line.startswith("allowed ips:"):
                current_peer.allowed_ips = line.split(":", 1)[1].strip()
            elif line.startswith("latest handshake:"):
                current_peer.latest_handshake = line.split(":", 1)[1].strip()
            elif line.startswith("transfer:"):
                parts = line.split(":", 1)[1].strip()
                if "received" in parts:
                    current_peer.transfer_rx = parts
                elif "sent" in parts:
                    current_peer.transfer_tx = parts
            elif line.startswith("persistent keepalive:"):
                current_peer.persistent_keepalive = line.split(":", 1)[1].strip()
    return info


def wg_quick_up(conf_path: str) -> str:
    """Activate a WireGuard interface from a .conf file."""
    return _run_wg(["quickup", conf_path], timeout=30)


def wg_quick_down(interface: str) -> str:
    """Deactivate a WireGuard interface."""
    return _run_wg(["quickdown", interface], timeout=15)


def wg_status() -> bool:
    """Check if WireGuard service is running (any interface)."""
    try:
        _run_wg(["show"], timeout=5)
        return True
    except KeyGenError:
        return False


def wg_interfaces() -> List[str]:
    """List active WireGuard interfaces."""
    raw = _run_wg(["show", "interfaces"], timeout=5)
    return [x.strip() for x in raw.split() if x.strip()]


def peer_count(interface: str = "") -> int:
    """Return number of peers for given (or default) interface."""
    info = wg_show(interface)
    return len(info.peers)
