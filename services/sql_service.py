"""SQL Server service — query and configure MSSQL via registry / sc / PowerShell / cmd.

All Windows-only. Tries PowerShell first; falls back to reg.exe + sc.exe (cmd)
for Win7 compatibility. Returns dummy data on non-Windows.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


def _server(instance: str) -> str:
    """连接地址：默认实例用 `.`，命名实例用 `.\\NAME`"""
    return "." if instance.upper() == "MSSQLSERVER" else f".\\{instance}"


class SqlListenMode(Enum):
    LOCAL = "127.0.0.1"
    ALL = "0.0.0.0"


@dataclass
class SqlInstanceInfo:
    version: str = ""
    state: str = ""
    agent_state: str = ""
    port: int = 65529
    tcp_enabled: bool = False
    listen_mode: SqlListenMode = SqlListenMode.LOCAL
    cluster: bool = False


def _has_powershell() -> bool:
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
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


def _cmd(args: list[str]) -> str:
    try:
        r = subprocess.run(
            ["cmd", "/c"] + args,
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


def _reg_query(key: str, value: str) -> str:
    return _cmd(["reg", "query", key, "/v", value])


def _reg_set(key: str, value: str, data: str, typ: str = "REG_SZ") -> str:
    return _cmd(["reg", "add", key, "/v", value, "/t", typ, "/d", data, "/f"])


def _reg_read_string(key: str, value: str) -> str:
    """Read a REG_SZ value from registry, return '' on failure."""
    raw = _reg_query(key, value)
    for line in raw.splitlines():
        if value in line:
            parts = line.rsplit(None, 1)
            if len(parts) >= 2:
                return parts[-1].strip()
    return ""


def _service_state(name: str) -> str:
    raw = _cmd(["sc", "query", name])
    # sc output: "STATE              : 4  RUNNING"
    for line in raw.splitlines():
        line = line.strip()
        if "STATE" in line:
            if "RUNNING" in line:
                return "Running"
            if "STOPPED" in line:
                return "Stopped"
    return "Unknown"


def _wait_for_service_state(name: str, target: str, timeout: int = 30) -> bool:
    """Poll sc query until service reaches target state. Returns True on success."""
    for _ in range(timeout):
        state = _service_state(name)
        if state == target:
            return True
        if state == "Unknown":
            return False
        time.sleep(1)
    return False


def _get_agent_state(svc_name: str) -> str:
    """SQL Agent state via WMI (SQL provider) → PS Get-Service → sc.exe.

    sc.exe doesn't reliably detect SQL Server Agent (returns empty on some
    installs). WMI via PowerShell avoids the dependency issue entirely.
    """
    if not _has_powershell():
        return _service_state(svc_name)

    # Try WMI namespaces for SQL 2008–2022
    for ns in [
        "root\\Microsoft\\SqlServer\\ComputerManagement10",  # 2008
        "root\\Microsoft\\SqlServer\\ComputerManagement11",  # 2012
        "root\\Microsoft\\SqlServer\\ComputerManagement12",  # 2014
        "root\\Microsoft\\SqlServer\\ComputerManagement13",  # 2016
        "root\\Microsoft\\SqlServer\\ComputerManagement14",  # 2017
        "root\\Microsoft\\SqlServer\\ComputerManagement15",  # 2019
        "root\\Microsoft\\SqlServer\\ComputerManagement16",  # 2022
    ]:
        state = _powershell(
            f"$svc = Get-WmiObject -Namespace '{ns}' -Query \"SELECT * FROM SqlService WHERE ServiceName='{svc_name}'\" -ErrorAction SilentlyContinue; "
            f"if ($svc) {{ $svc.State }}"
        )
        # WMI State: 1=Stopped, 2=StartPending, 3=StopPending, 4=Running
        if state and not state.startswith("<error:") and state.isdigit():
            return "Running" if state == "4" else "Stopped"

    # Fallback: PS Get-Service
    svc = _powershell(
        f'Get-Service -Name "{svc_name}" -ErrorAction SilentlyContinue '
        f"| Select-Object -ExpandProperty Status"
    )
    if "Running" in svc:
        return "Running"
    if "Stopped" in svc:
        return "Stopped"
    return "Unknown"


def _instance_service(instance: str) -> str:
    return "MSSQLSERVER" if instance.upper() == "MSSQLSERVER" else f"MSSQL${instance}"


def _agent_service(instance: str) -> str:
    return "SQLSERVERAGENT" if instance.upper() == "MSSQLSERVER" else f"SQLSERVERAGENT${instance}"


# ── registry path ────────────────────────────────────────────────


def _reg_path(instance: str) -> str:
    """Resolve TCP/IPAll registry path via Instance Names, fallback to legacy."""
    raw = _cmd([
        "reg", "query",
        r"HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL",
        "/v", instance,
    ])
    for line in raw.splitlines():
        if instance in line and "REG_SZ" in line:
            subkey = line.rsplit(None, 1)[-1].strip()
            return (
                f"HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
                f"{subkey}\\MSSQLServer\\SuperSocketNetLib\\Tcp"
            )
    # Fallback: legacy path (SQL 2008-) for default, guess for named
    if instance.upper() == "MSSQLSERVER":
        return (
            r"HKLM\SOFTWARE\Microsoft\MSSQLServer"
            r"\MSSQLServer\SuperSocketNetLib\Tcp"
        )
    return (
        f"HKLM\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
        f"MSSQL${instance}\\MSSQLServer\\SuperSocketNetLib\\Tcp"
    )


def _version_reg_path(instance: str) -> str:
    """Registry key holding CurrentVersion for the instance."""
    if instance.upper() == "MSSQLSERVER":
        return r"HKLM\SOFTWARE\Microsoft\MSSQLServer\MSSQLServer"
    # ponytail: named-instance version lookup — add when actually needed
    return ""


# ── public API ───────────────────────────────────────────────────


def get_sql_info(instance: str = "MSSQLSERVER") -> SqlInstanceInfo:
    """Query SQL Server instance info."""
    info = SqlInstanceInfo()

    if sys.platform != "win32":
        info.version = "n/a (non-Windows)"
        info.state = "unknown"
        return info

    # Engine service state — sc.exe (reliable, English output on all locales)
    svc_name = _instance_service(instance)
    info.state = _service_state(svc_name)
    logger.info("Service '%s' state: %s", svc_name, info.state)

    # Agent state
    agent_svc = _agent_service(instance)
    info.agent_state = _get_agent_state(agent_svc)

    # Registry reads — reg.exe only (PS path had "HKLM:HKLM\..." bug)
    rp = _reg_path(instance)

    # Port from registry
    port_raw = _reg_read_string(rp, "TcpPort")
    if port_raw and not port_raw.startswith("<error:"):
        try:
            info.port = int(port_raw)
        except ValueError:
            pass
    # Tcp subkey exists with TcpPort → TCP enabled
    info.tcp_enabled = True
    # Listen mode (ListenAll may not exist, defaults to 127.0.0.1)
    listen_raw = _reg_read_string(rp, "ListenAll")
    info.listen_mode = SqlListenMode.ALL if listen_raw.strip() == "1" else SqlListenMode.LOCAL

    # Optional sqlcmd verification — best-effort, never overrides registry
    addr = _server(instance)
    try:
        r = subprocess.run(
            ["sqlcmd", "-S", addr, "-E", "-h", "-1", "-Q",
             "SET NOCOUNT ON; SELECT local_tcp_port FROM sys.dm_exec_connections WHERE session_id = @@SPID"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.isdigit() and 1 <= int(line) <= 65535:
                info.port = int(line)
    except Exception:
        pass

    # Version
    ver_path = _version_reg_path(instance)
    if ver_path:
        ver = _reg_read_string(ver_path, "CurrentVersion")
        if ver and not ver.startswith("<error:"):
            info.version = ver.strip()

    logger.info("SQL info: port=%d tcp=%s listen=%s", info.port, info.tcp_enabled, info.listen_mode.value)
    return info


def set_sql_port(port: int, instance: str = "MSSQLSERVER") -> str:
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    result = _reg_set(_reg_path(instance), "TcpPort", str(port))
    return "OK" if "error" not in result.lower() else result


def set_sql_listen_mode(mode: SqlListenMode, instance: str = "MSSQLSERVER") -> str:
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    r = _reg_set(_reg_path(instance), "ListenAll",
                  "1" if mode == SqlListenMode.ALL else "0")
    return "OK" if "error" not in r.lower() else r


def restart_sql(instance: str = "MSSQLSERVER") -> str:
    """Restart SQL Server via T-SQL SHUTDOWN (reliable, bypasses SCM)."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    svc_name = _instance_service(instance)
    try:
        subprocess.run(
            ["sqlcmd", "-S", _server(instance), "-E", "-Q", "SHUTDOWN WITH NOWAIT"],
            capture_output=True, timeout=60,
        )
    except Exception:
        pass
    for _ in range(60):
        state = _service_state(svc_name)
        if state == "Running":
            return "OK"
        if state != "Unknown":
            time.sleep(1)
    return "✗ SHUTDOWN 后服务未自动重启"


def restart_sql_agent(instance: str = "MSSQLSERVER") -> str:
    """Restart SQL Server Agent service."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    return _restart_service(_agent_service(instance))
