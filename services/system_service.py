"""System service — ping, traceroute, public IP, system info."""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import time
import re
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


def service_state(service_name: str) -> str:
    """Return Running, Stopped, or Unknown for a Windows service."""
    if sys.platform != "win32":
        return "Unknown"
    try:
        result = subprocess.run(["sc", "query", service_name], capture_output=True,
                                text=True, timeout=15, encoding="utf-8", errors="replace")
        output = result.stdout + result.stderr
        # sc.exe's text is localized, but the numeric state is stable:
        # 1=STOPPED, 2=START_PENDING, 3=STOP_PENDING, 4=RUNNING.
        match = re.search(r"STATE\s*:\s*(\d+)", output, re.IGNORECASE)
        if match:
            state = int(match.group(1))
            if state == 4:
                return "Running"
            if state == 1:
                return "Stopped"
            if state == 2:
                return "Starting"
            if state == 3:
                return "Stopping"
        upper = output.upper()
        if "RUNNING" in upper:
            return "Running"
        if "STOPPED" in upper:
            return "Stopped"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "Unknown"


def restart_service(service_name: str) -> str:
    """Restart a Windows service and verify that it reaches Running."""
    if sys.platform != "win32":
        return f"n/a: restart '{service_name}' is Windows-only"

    import subprocess
    try:
        state = service_state(service_name)
        if state == "Unknown":
            return f"Service '{service_name}' was not found or cannot be queried"
        if state == "Running":
            result = subprocess.run(["sc.exe", "stop", service_name], capture_output=True,
                                    text=True, timeout=30, encoding="utf-8", errors="replace")
            if result.returncode != 0:
                detail = (result.stderr.strip() or result.stdout.strip() or "unknown error")
                return f"Failed to stop '{service_name}': {detail}"
            for _ in range(30):
                if service_state(service_name) == "Stopped":
                    break
                time.sleep(1)
            else:
                return f"Timed out stopping '{service_name}'"
        result = subprocess.run(["sc.exe", "start", service_name], capture_output=True,
                                text=True, timeout=30, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            detail = (result.stderr.strip() or result.stdout.strip() or "unknown error")
            return f"Failed to start '{service_name}': {detail}"
        for _ in range(30):
            if service_state(service_name) == "Running":
                return f"Service '{service_name}' restarted"
            time.sleep(1)
        return f"Timed out starting '{service_name}'"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Failed: {exc}"
