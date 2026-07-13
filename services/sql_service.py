"""SQL Server service — query and configure MSSQL via registry / sc / PowerShell / cmd.

All Windows-only. Tries PowerShell first; falls back to reg.exe + sc.exe (cmd)
for Win7 compatibility. Returns dummy data on non-Windows.
"""
from __future__ import annotations

import subprocess
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


def _has_powershell() -> bool:
    """Quick check: is powershell.exe on PATH?"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "echo 1"],
            capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _powershell(script: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


def _cmd(args: list[str]) -> str:
    """Run a cmd.exe command, return stdout."""
    try:
        r = subprocess.run(
            ["cmd", "/c"] + args,
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


def _reg_query(key: str, value: str) -> str:
    """Read registry value via reg.exe."""
    return _cmd(["reg", "query", key, "/v", value])


def _reg_set(key: str, value: str, data: str, typ: str = "REG_SZ") -> str:
    """Write registry value via reg.exe."""
    return _cmd(["reg", "add", key, "/v", value, "/t", typ, "/d", data, "/f"])


def _service_state(name: str) -> str:
    """Get service state via sc.exe."""
    raw = _cmd(["sc", "query", name])
    for line in raw.splitlines():
        line = line.strip()
        if "STATE" in line:
            if "RUNNING" in line:
                return "Running"
            if "STOPPED" in line:
                return "Stopped"
    return "Unknown"


def _reg_path(instance: str) -> str:
    """Resolve SQL Server instance registry key."""
    # 1. Instance Names\SQL
    raw = _cmd([
        "reg", "query", 
        "HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\Instance Names\\SQL",
        "/v", instance,
    ])
    for line in raw.splitlines():
        if instance in line and "REG_SZ" in line:
            subkey = line.rsplit(None, 1)[-1].strip()
            return (
                f"HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
                f"{subkey}\\MSSQLServer\\SuperSocketNetLib\\Tcp\\IPAll"
            )
    # 2. Search for subkey containing instance name
    raw = _cmd([
        "reg", "query",
        "HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server",
        "/s", "/f", instance, "/k",
    ])
    for line in raw.splitlines():
        line = line.strip()
        if instance in line and "MSSQLServer" in line:
            return (
                f"{line}\\SuperSocketNetLib\\Tcp\\IPAll"
            )
    # 3. Hardcoded fallback
    return (
        f"HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
        f"MSSQL{instance}\\MSSQLServer\\SuperSocketNetLib\\Tcp\\IPAll"
    )


def _instance_service(instance: str) -> str:
    """Return the Windows service name for a SQL instance.
    Default instance → 'MSSQLSERVER', named → 'MSSQL$Instance'.
    """
    return "MSSQLSERVER" if instance.upper() == "MSSQLSERVER" else f"MSSQL${instance}"


def _agent_service(instance: str) -> str:
    """Return the Windows service name for SQL Agent.
    Default instance → 'SQLSERVERAGENT', named → 'SQLSERVERAGENT$Instance'.
    """
    return "SQLSERVERAGENT" if instance.upper() == "MSSQLSERVER" else f"SQLSERVERAGENT${instance}"


def get_sql_info(instance: str = "MSSQLSERVER") -> SqlInstanceInfo:
    """Query SQL Server instance info."""
    info = SqlInstanceInfo()
    use_ps = _has_powershell()

    if sys.platform != "win32":
        info.version = "n/a (non-Windows)"
        info.state = "unknown"
        return info

    # Service state
    svc_name = _instance_service(instance)
    if use_ps:
        svc = _powershell(
            f'Get-Service -Name "{svc_name}" -ErrorAction SilentlyContinue '
            f"| Select-Object -Property Status"
        )
        info.state = "Running" if "Running" in svc else (
            "Stopped" if "Stopped" in svc else "Unknown"
        )
    else:
        info.state = _service_state(_instance_service(instance))

    rp = _reg_path(instance)

    # TCP port
    if use_ps:
        port_raw = _powershell(
            f'(Get-ItemProperty -Path "HKLM:{rp}" '
            f"-Name TcpPort -ErrorAction SilentlyContinue).TcpPort"
        )
    else:
        raw = _reg_query(rp, "TcpPort")
        # reg.exe output: "    TcpPort    REG_SZ    65529"
        for line in raw.splitlines():
            if "TcpPort" in line:
                port_raw = line.rsplit(None, 1)[-1].strip()
                break
        else:
            port_raw = ""

    if port_raw and not port_raw.startswith("<error:"):
        try:
            info.port = int(port_raw)
        except ValueError:
            pass

    # TCP/IP enabled
    if use_ps:
        tcp_en = _powershell(
            f'(Get-ItemProperty -Path "HKLM:{rp}" '
            f"-Name Enabled -ErrorAction SilentlyContinue).Enabled"
        )
    else:
        raw = _reg_query(rp, "Enabled")
        for line in raw.splitlines():
            if "Enabled" in line:
                tcp_en = line.rsplit(None, 1)[-1].strip()
                break
        else:
            tcp_en = ""
    info.tcp_enabled = tcp_en.strip() == "1"

    # Listen mode
    if use_ps:
        listen_all = _powershell(
            f'(Get-ItemProperty -Path "HKLM:{rp}" '
            f"-Name ListenAll -ErrorAction SilentlyContinue).ListenAll"
        )
    else:
        raw = _reg_query(rp, "ListenAll")
        for line in raw.splitlines():
            if "ListenAll" in line:
                listen_all = line.rsplit(None, 1)[-1].strip()
                break
        else:
            listen_all = ""
    info.listen_mode = SqlListenMode.ALL if listen_all.strip() == "1" else SqlListenMode.LOCAL

    # Version
    if use_ps:
        ver = _powershell(
            '(Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\'
            'Microsoft SQL Server\\" '
            "-ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty CurrentVersion)"
        )
    else:
        ver = _cmd([
            "reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server",
            "/v", "CurrentVersion",
        ])
        for line in ver.splitlines():
            if "CurrentVersion" in line:
                ver = line.rsplit(None, 1)[-1].strip()
                break
        else:
            ver = ""

    if ver and not ver.startswith("<error:"):
        info.version = ver.strip()

    return info


def set_sql_port(port: int, instance: str = "MSSQLSERVER") -> str:
    """Set SQL Server TCP port via registry."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    rp = _reg_path(instance)

    if _has_powershell():
        return _powershell(
            f'Set-ItemProperty -Path "HKLM:{rp}" '
            f'-Name TcpPort -Value "{port}" -ErrorAction Stop; echo "OK"'
        )
    else:
        result = _reg_set(rp, "TcpPort", str(port))
        return "OK" if "error" not in result.lower() else result


def set_sql_listen_mode(
    mode: SqlListenMode, instance: str = "MSSQLSERVER"
) -> str:
    """Set SQL Server listen mode (127.0.0.1 or 0.0.0.0)."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    rp = _reg_path(instance)
    listen_all = "1" if mode == SqlListenMode.ALL else "0"

    if _has_powershell():
        return _powershell(
            f'Set-ItemProperty -Path "HKLM:{rp}" '
            f'-Name ListenAll -Value {listen_all} -ErrorAction Stop; echo "OK"'
        )
    else:
        result = _reg_set(rp, "ListenAll", listen_all)
        return "OK" if "error" not in result.lower() else result


def restart_sql(instance: str = "MSSQLSERVER") -> str:
    """Restart SQL Server service."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    svc_name = _instance_service(instance)

    if _has_powershell():
        return _powershell(
            f'Restart-Service -Name "{svc_name}" -Force -ErrorAction Stop; '
            f"echo 'Restarted'"
        )
    else:
        _cmd(["sc", "stop", svc_name])
        _cmd(["sc", "start", svc_name])
        return "Restarted"
