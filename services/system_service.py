"""System service — ping, traceroute, public IP, system info."""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SystemInfo:
    hostname: str = ""
    os_version: str = ""
    cpu_count: int = 0
    total_ram_gb: float = 0.0
    uptime_days: float = 0.0
    ip_addresses: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0


def ping(host: str, count: int = 4) -> str:
    """Ping a host, return raw output."""
    flag = "-n" if sys.platform == "win32" else "-c"
    try:
        r = subprocess.run(
            ["ping", flag, str(count), host],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout.strip() or r.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Ping timed out"
    except FileNotFoundError:
        return "ping not found on this system"


def traceroute(host: str) -> str:
    """Traceroute to a host."""
    cmd = ["tracert" if sys.platform == "win32" else "traceroute", host]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )
        return r.stdout.strip() or r.stderr.strip()
    except subprocess.TimeoutExpired:
        return "Traceroute timed out"
    except FileNotFoundError:
        return "traceroute not found on this system"


def public_ip() -> str:
    """Detect public IP via external service."""
    import urllib.request
    try:
        with urllib.request.urlopen(
            "https://api.ipify.org", timeout=10
        ) as resp:
            return resp.read().decode().strip()
    except Exception as exc:
        try:
            with urllib.request.urlopen(
                "https://checkip.amazonaws.com", timeout=10
            ) as resp:
                return resp.read().decode().strip()
        except Exception:
            return f"Failed to detect: {exc}"


def get_system_info() -> SystemInfo:
    """Gather basic system information."""
    info = SystemInfo()
    info.hostname = platform.node()
    info.os_version = f"{platform.system()} {platform.release()} {platform.version()}"
    info.cpu_count = os.cpu_count() or 0

    try:
        import psutil
        info.total_ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        info.uptime_days = round((__import__("time").time() - psutil.boot_time()) / 86400, 1)
        info.cpu_percent = psutil.cpu_percent(interval=0.5)
        info.memory_percent = psutil.virtual_memory().percent
        info.disk_percent = psutil.disk_usage("/").percent
    except ImportError:
        info.total_ram_gb = 0.0
        info.uptime_days = 0.0

    # IPs
    try:
        ips = []
        for entry in socket.getaddrinfo(socket.gethostname(), None):
            ip = entry[4][0]
            if ip and not ip.startswith("127.") and ":" not in ip:
                ips.append(ip)
        info.ip_addresses = ", ".join(sorted(set(ips)))
    except Exception:
        info.ip_addresses = "unknown"

    return info


def restart_service(service_name: str) -> str:
    """Restart a Windows service (or return message on other platforms)."""
    if sys.platform != "win32":
        return f"n/a: restart '{service_name}' is Windows-only"

    import subprocess
    try:
        r = subprocess.run(
            ["sc", service_name, "stop"], capture_output=True, text=True, timeout=30,
        )
        r = subprocess.run(
            ["sc", service_name, "start"], capture_output=True, text=True, timeout=30,
        )
        return f"Service '{service_name}' restarted"
    except Exception as exc:
        return f"Failed: {exc}"
