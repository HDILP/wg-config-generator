"""SQL Server service — query and configure MSSQL via registry / sc / PowerShell.

All Windows-only; returns dummy data on other platforms for development.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SqlListenMode(Enum):
    LOCAL = "127.0.0.1"
    ALL = "0.0.0.0"


@dataclass
class SqlInstanceInfo:
    version: str = ""
    state: str = ""
    port: int = 65529
    tcp_enabled: bool = False
    listen_mode: SqlListenMode = SqlListenMode.LOCAL
    cluster: bool = False


def _powershell(script: str) -> str:
    """Run a PowerShell command and return stdout."""
    import subprocess
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


def get_sql_info(instance: str = "MSSQLSERVER") -> SqlInstanceInfo:
    """Query SQL Server instance info via registry (Windows) or return defaults."""
    info = SqlInstanceInfo()

    if sys.platform != "win32":
        info.version = "n/a (non-Windows)"
        info.state = "unknown"
        info.tcp_enabled = False
        return info

    # Check service status
    svc = _powershell(
        f'Get-Service -Name "MSSQL${instance}" -ErrorAction SilentlyContinue '
        f"| Select-Object -Property Status, DisplayName"
    )
    if "Running" in svc:
        info.state = "Running"
    elif "Stopped" in svc:
        info.state = "Stopped"
    else:
        info.state = "Unknown"

    # Registry: TCP port
    reg_path = (
        f"HKLM:\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
        f"MSSQL{instance}\\MSSQLServer\\SuperSocketNetLib\\Tcp\\IPAll"
    )
    port_raw = _powershell(
        f'(Get-ItemProperty -Path "{reg_path}" -Name TcpPort '
        f"-ErrorAction SilentlyContinue).TcpPort"
    )
    if port_raw and port_raw != "<error:":
        try:
            info.port = int(port_raw)
        except ValueError:
            pass

    # TCP dynamic ports
    dyn_raw = _powershell(
        f'(Get-ItemProperty -Path "{reg_path}" -Name TcpDynamicPorts '
        f"-ErrorAction SilentlyContinue).TcpDynamicPorts"
    )
    if dyn_raw and dyn_raw != "0" and "<error:" not in dyn_raw:
        pass  # dynamic port, trust the static port

    # TCP/IP enabled
    tcp_en = _powershell(
        f'(Get-ItemProperty -Path "{reg_path}" -Name Enabled '
        f"-ErrorAction SilentlyContinue).Enabled"
    )
    info.tcp_enabled = tcp_en.strip() == "1"

    # Listen mode: check IP1/IP2/IPAll — if any non-127.0.0.1, assume ALL
    # ponytail: read IPAll's ListenAll, fallback to IP1
    listen_all = _powershell(
        f'(Get-ItemProperty -Path "{reg_path}" -Name ListenAll '
        f"-ErrorAction SilentlyContinue).ListenAll"
    )
    info.listen_mode = SqlListenMode.ALL if listen_all.strip() == "1" else SqlListenMode.LOCAL

    # Version
    ver = _powershell(
        '(Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\" '
        "-ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty CurrentVersion)"
    )
    if ver and "<error:" not in ver:
        info.version = ver.strip()

    return info


def set_sql_port(port: int, instance: str = "MSSQLSERVER") -> str:
    """Set SQL Server TCP port via registry."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    reg_path = (
        f"HKLM:\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
        f"MSSQL{instance}\\MSSQLServer\\SuperSocketNetLib\\Tcp\\IPAll"
    )
    result = _powershell(
        f'Set-ItemProperty -Path "{reg_path}" -Name TcpPort -Value "{port}" '
        f" -ErrorAction Stop; echo 'OK'"
    )
    return result


def set_sql_listen_mode(
    mode: SqlListenMode, instance: str = "MSSQLSERVER"
) -> str:
    """Set SQL Server listen mode (127.0.0.1 or 0.0.0.0)."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    reg_path = (
        f"HKLM:\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
        f"MSSQL{instance}\\MSSQLServer\\SuperSocketNetLib\\Tcp\\IPAll"
    )
    listen_all = "1" if mode == SqlListenMode.ALL else "0"
    result = _powershell(
        f'Set-ItemProperty -Path "{reg_path}" -Name ListenAll -Value {listen_all} '
        f"-ErrorAction Stop; echo 'OK'"
    )
    return result


def restart_sql(instance: str = "MSSQLSERVER") -> str:
    """Restart SQL Server service."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    return _powershell(
        f'Restart-Service -Name "MSSQL${instance}" -Force -ErrorAction Stop; '
        f"echo 'Restarted'"
    )
