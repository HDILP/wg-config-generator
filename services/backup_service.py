"""Backup Center — SQL Server backup service.

PowerShell + System.Data.SqlClient for Win7+ compatibility.
Falls back to sqlcmd/osql when PowerShell is unavailable.
All backup config lives in project.json (BackupPolicy).
History stored in <project>/backup_history.json.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.backup import BackupPolicy
from models.project import Project
from services.sql_service import _server
from utils.file_ops import ensure_dir, read_json, write_json

logger = logging.getLogger(__name__)


@dataclass
class BackupHistoryEntry:
    database: str = ""
    status: str = ""          # "success" / "failed"
    size_mb: float = 0.0
    duration_sec: float = 0.0
    path: str = ""
    error: str = ""
    timestamp: str = ""


# ═════════════════════════════════════════════════════════════════
#  PowerShell helpers
# ═════════════════════════════════════════════════════════════════

def _has_powershell() -> bool:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "echo 1"],
            capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _ps(script: str, timeout: int = 60) -> Tuple[str, str]:
    """Run a PowerShell script, return (stdout, stderr)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip(), r.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return "", str(exc)


def _conn_str(instance: str = "MSSQLSERVER") -> str:
    return f"Server={_server(instance)};Database=master;Integrated Security=SSPI;Trusted_Connection=True;"


# ═════════════════════════════════════════════════════════════════
#  Database queries
# ═════════════════════════════════════════════════════════════════

def list_databases(instance: str = "MSSQLSERVER") -> List[str]:
    """Query sys.databases, return user databases sorted by name."""
    if sys.platform != "win32":
        return ["master", "model", "msdb", "tempdb", "GraspCRM_Shenzhen", "GraspCRM_Guangzhou"]

    system_dbs = {"master", "model", "msdb", "tempdb"}
    script = f"""
$conn = New-Object System.Data.SqlClient.SqlConnection("{_conn_str(instance)}")
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandText = "SELECT name FROM sys.databases ORDER BY name"
$rdr = $cmd.ExecuteReader()
$list = @()
while ($rdr.Read()) {{ $list += $rdr.GetString(0) }}
$rdr.Close(); $conn.Close()
$list -join "`n"
"""
    logger.info("Listing databases via PowerShell SqlClient on %s", _server(instance))
    out, err = _ps(script, timeout=15)
    if not out or out.startswith("<error"):
        # Fallback: try sqlcmd
        addr = _server(instance)
        logger.info("PS failed, trying sqlcmd -S %s", addr)
        try:
            r = subprocess.run(
                ["sqlcmd", "-S", addr, "-E", "-Q", "SET NOCOUNT ON; SELECT name FROM sys.databases ORDER BY name"],
                capture_output=True, text=True, timeout=15,
            )
            out = r.stdout.strip()
            if not out:
                raise RuntimeError(f"sqlcmd 返回空结果 — stderr: {r.stderr.strip()}")
        except (FileNotFoundError, OSError) as exc:
            raise RuntimeError(f"sqlcmd 找不到 — 需要安装 SQL Server 命令行工具 ({exc})") from exc

    return [d.strip() for d in out.splitlines()
            if d.strip() and d.strip() not in system_dbs]


def get_db_sizes(instance: str = "MSSQLSERVER") -> Dict[str, float]:
    """Return {db_name: size_mb} for all user databases."""
    if sys.platform != "win32":
        return {"GraspCRM_Shenzhen": 2048.0, "GraspCRM_Guangzhou": 4096.0}

    script = f"""
$conn = New-Object System.Data.SqlClient.SqlConnection("{_conn_str(instance)}")
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandText = @"
SELECT d.name, CAST(SUM(CAST(mf.size AS BIGINT)) * 8.0 / 1024 AS DECIMAL(10,1))
FROM sys.databases d
JOIN sys.master_files mf ON d.database_id = mf.database_id
WHERE d.name NOT IN ('master','model','msdb','tempdb')
GROUP BY d.name
ORDER BY d.name
"@
$rdr = $cmd.ExecuteReader()
$lines = @()
while ($rdr.Read()) {{ $lines += "$($rdr.GetString(0))|$($rdr.GetDecimal(1))" }}
$rdr.Close(); $conn.Close()
$lines -join "`n"
"""
    out, err = _ps(script)
    sizes: Dict[str, float] = {}
    for line in out.splitlines():
        if "|" in line:
            name, size = line.rsplit("|", 1)
            try:
                sizes[name.strip()] = float(size.strip())
            except ValueError:
                pass
    return sizes


def check_compression_support(instance: str = "MSSQLSERVER") -> bool:
    """Check if SQL Server supports backup compression via sqlcmd."""
    if sys.platform != "win32":
        return True
    try:
        r = subprocess.run(
            ["sqlcmd", "-S", _server(instance), "-E", "-h", "-1",
             "-Q", "SET NOCOUNT ON; SELECT value FROM sys.configurations WHERE name = 'backup compression default'"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip() == "1"
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════
#  Backup execution
# ═════════════════════════════════════════════════════════════════

def _backup_dir(policy: BackupPolicy, timestamp: Optional[datetime] = None) -> Path:
    """Generate backup path: D:/SQLBackup/YYYY/MM/DD."""
    ts = timestamp or datetime.now()
    return Path(policy.save_path) / str(ts.year) / f"{ts.month:02d}" / f"{ts.day:02d}"


def _backup_filename(db_name: str, timestamp: Optional[datetime] = None) -> str:
    ts = timestamp or datetime.now()
    return f"{db_name}_{ts.strftime('%Y%m%d_%H%M%S')}.bak"


def immediate_backup(
    project: Project,
    databases: List[str],
    progress_cb=None,
) -> List[BackupHistoryEntry]:
    """Run immediate backup for selected databases. Returns history entries."""
    policy = project.settings.backup
    instance = project.settings.sql.instance
    history: List[BackupHistoryEntry] = []
    ts = datetime.now()
    bdir = _backup_dir(policy, ts)
    ensure_dir(bdir)

    for i, db in enumerate(databases):
        if progress_cb:
            progress_cb(i, len(databases), db)

        fname = _backup_filename(db, ts)
        fpath = bdir / fname
        entry = BackupHistoryEntry(
            database=db,
            timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
            path=str(fpath),
        )

        try:
            compression = "WITH COMPRESSION, INIT, FORMAT" if policy.compression else "WITH INIT, FORMAT"
            result = _exec_sql(
                instance,
                f"BACKUP DATABASE [{db}] TO DISK='{fpath}' {compression}",
            )
            if "error" not in result.lower() and result.strip():
                entry.status = "success"
                # Parse backup size from output
                for line in result.splitlines():
                    if "MB" in line or "MB" in line.upper():
                        import re
                        m = re.search(r"([\d.]+)\s*MB", line, re.IGNORECASE)
                        if m:
                            entry.size_mb = float(m.group(1))
                            break
                entry.duration_sec = (datetime.now() - ts).total_seconds()
            else:
                entry.status = "failed"
                entry.error = result[:200]
        except Exception as exc:
            entry.status = "failed"
            entry.error = str(exc)

        history.append(entry)
        _append_history(project, entry)

    return history


def _exec_sql(instance: str, query: str, timeout: int = 300) -> str:
    """Execute a SQL query against the server. Returns stdout."""
    if sys.platform != "win32":
        return f"[mock] {query[:60]}..."

    addr = _server(instance)
    logger.info("SQL: %s — %.80s", addr, query.replace("\n", " "))

    if _has_powershell():
        sq = query.replace("'", "''")
        script = f"""
$conn = New-Object System.Data.SqlClient.SqlConnection("{_conn_str(instance)}")
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandTimeout = {timeout}
$cmd.CommandText = '{sq}'
if ($cmd.CommandText.TrimStart().StartsWith('SELECT') -or $cmd.CommandText.TrimStart().StartsWith('EXEC')) {{
    $rdr = $cmd.ExecuteReader()
    $lines = @()
    do {{ while ($rdr.Read()) {{
        $vals = for ($i=0; $i -lt $rdr.FieldCount; $i++) {{ $rdr.GetValue($i).ToString() }}
        $lines += ($vals -join "|")
    }} }} while ($rdr.NextResult())
    $rdr.Close()
    $lines -join "`n"
}} else {{
    $cmd.ExecuteNonQuery() | Out-Null
    "OK"
}}
$conn.Close()
"""
        out, err = _ps(script, timeout=timeout + 30)
        if out and not out.startswith("<error"):
            return out
        logger.warning("PS query failed: %.100s", err or out)
    else:
        # Fallback: sqlcmd
        try:
            r = subprocess.run(
                ["sqlcmd", "-S", addr, "-Q", f"SET NOCOUNT ON; {query}"],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
            return r.stdout.strip() or r.stderr.strip()
        except (FileNotFoundError, OSError) as exc:
            logger.error("sqlcmd not found: %s", exc)
            return f"error: sqlcmd not found — {exc}"


# ═════════════════════════════════════════════════════════════════
#  Restore
# ═════════════════════════════════════════════════════════════════

def restore_database(
    instance: str,
    bak_path: str,
    target_db: str,
    overwrite: bool = False,
) -> str:
    """Restore a database from a .bak file."""
    replace = ", REPLACE" if overwrite else ""
    query = f"RESTORE DATABASE [{target_db}] FROM DISK='{bak_path}' WITH RECOVERY{replace}"
    return _exec_sql(instance, query, timeout=600)


def get_backup_databases(bak_path: str, instance: str = "MSSQLSERVER") -> List[str]:
    """List databases contained in a .bak file (file list only)."""
    query = f"RESTORE FILELISTONLY FROM DISK='{bak_path}'"
    return _exec_sql(instance, query, timeout=30).splitlines()


# ═════════════════════════════════════════════════════════════════
#  Windows Task Scheduler
# ═════════════════════════════════════════════════════════════════

def _task_name(project: Project) -> str:
    return f"GP Backup - {project.name}"


def _generate_backup_script(project: Project) -> str:
    """Generate a .ps1 file that performs the scheduled backup."""
    policy = project.settings.backup
    instance = project.settings.sql.instance
    dbs = "', '".join(policy.databases)
    save = policy.save_path.replace("\\", "\\\\")
    comp = "$true" if policy.compression else "$false"
    retention = policy.retention_days

    return f"""# GP Server Manager — Auto Backup
# Project: {project.name}
$dbs = '{dbs}' -split "', '"
$savePath = "{save}"
$compression = ${comp}
$retention = {retention}
$instance = "{instance}"
$serverAddr = if ($instance -eq 'MSSQLSERVER') {{ '.' }} else {{ ".\\$instance" }}
$ts = Get-Date -Format "yyyy/MM/dd/HHmmss"
$connStr = "Server=$serverAddr;Database=master;Integrated Security=SSPI;"

foreach ($db in $dbs) {{
    if (-not $db) {{ continue }}
    $dir = Join-Path $savePath (Get-Date -Format "yyyy/MM/dd")
    $null = New-Item -ItemType Directory -Path $dir -Force
    $fname = "$db{'_'}$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
    $fpath = Join-Path $dir $fname
    try {{
        $conn = New-Object System.Data.SqlClient.SqlConnection($connStr)
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandTimeout = 600
        if ($compression) {{
            $cmd.CommandText = "BACKUP DATABASE [$db] TO DISK='$fpath' WITH COMPRESSION, INIT, FORMAT"
        }} else {{
            $cmd.CommandText = "BACKUP DATABASE [$db] TO DISK='$fpath' WITH INIT, FORMAT"
        }}
        $cmd.ExecuteNonQuery()
        $conn.Close()
        Write-Output "OK:$db"
    }} catch {{
        Write-Output "FAIL:$db`:$_"
    }}
}}

# Cleanup old backups
$cutoff = (Get-Date).AddDays(-$retention)
Get-ChildItem -Path $savePath -Recurse -Filter "*.bak" | Where-Object {{
    $_.LastWriteTime -lt $cutoff
}} | Remove-Item -Force
"""


def create_scheduled_task(project: Project) -> str:
    """Create or update Windows scheduled task for backup."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    policy = project.settings.backup
    if not policy.databases:
        return "No databases selected"

    # Write .ps1 script
    ps_dir = ensure_dir(project.dir / "scripts")
    ps_path = ps_dir / "auto_backup.ps1"
    ps_path.write_text(_generate_backup_script(project), encoding="utf-8")

    # Parse schedule time
    parts = policy.schedule_time.split(":")
    hour = parts[0] if len(parts) > 0 else "2"
    minute = parts[1] if len(parts) > 1 else "0"

    task_name = _task_name(project)
    ps_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps_path}"'

    # Use schtasks.exe (available on Win7+)
    try:
        # Delete existing task first
        subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True, timeout=10,
        )
    except (FileNotFoundError, OSError):
        pass

    try:
        r = subprocess.run(
            ["schtasks", "/create", "/tn", task_name, "/tr", ps_cmd,
             "/sc", "daily", "/st", f"{hour}:{minute}:00",
             "/rl", "HIGHEST", "/f"],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip()
    except (FileNotFoundError, OSError) as exc:
        return f"error: {exc}"


def remove_scheduled_task(project: Project) -> str:
    """Remove the Windows scheduled task for this project."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    task_name = _task_name(project)
    try:
        r = subprocess.run(
            ["schtasks", "/delete", "/tn", task_name, "/f"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip()
    except (FileNotFoundError, OSError) as exc:
        return f"error: {exc}"


def get_scheduled_task_status(project: Project) -> Optional[str]:
    """Check if the scheduled task exists. Returns status string or None."""
    if sys.platform != "win32":
        return "n/a"

    task_name = _task_name(project)
    try:
        r = subprocess.run(
            ["schtasks", "/query", "/tn", task_name, "/fo", "LIST"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                line = line.strip()
                if "Status" in line or "状态" in line:
                    return line.split(":", 1)[-1].strip()
            return "Created"
        return None
    except (FileNotFoundError, OSError):
        return None


# ═════════════════════════════════════════════════════════════════
#  Backup history
# ═════════════════════════════════════════════════════════════════

def _history_path(project: Project) -> Path:
    return project.dir / "backup_history.json"


def _read_history(project: Project) -> List[Dict]:
    path = _history_path(project)
    if path.exists():
        try:
            return read_json(path)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _write_history(project: Project, entries: List[Dict]) -> None:
    ensure_dir(_history_path(project).parent)
    write_json(_history_path(project), entries)


def _append_history(project: Project, entry: BackupHistoryEntry) -> None:
    entries = _read_history(project)
    entries.append({
        "database": entry.database,
        "status": entry.status,
        "size_mb": entry.size_mb,
        "duration_sec": entry.duration_sec,
        "path": entry.path,
        "error": entry.error,
        "timestamp": entry.timestamp,
    })
    # Keep last 500 entries
    if len(entries) > 500:
        entries = entries[-500:]
    _write_history(project, entries)


def get_backup_history(project: Project, limit: int = 50) -> List[Dict]:
    """Get recent backup history, newest first."""
    entries = _read_history(project)
    entries.reverse()
    return entries[:limit]


# ═════════════════════════════════════════════════════════════════
#  Health
# ═════════════════════════════════════════════════════════════════

@dataclass
class BackupHealth:
    status: str = "unknown"        # "ok" / "warning" / "error"
    last_success: str = ""
    last_failed: str = ""
    last_failed_db: str = ""
    remaining_gb: float = 0.0
    total_dbs: int = 0
    ok_dbs: int = 0
    failed_dbs: int = 0


def get_backup_health(project: Project) -> BackupHealth:
    """Evaluate backup health from history."""
    health = BackupHealth()
    history = _read_history(project)
    if not history:
        health.status = "unknown"
        return health

    success_entries = [h for h in history if h.get("status") == "success"]
    failed_entries = [h for h in history if h.get("status") == "failed"]

    if success_entries:
        health.last_success = success_entries[0].get("timestamp", "")
    if failed_entries:
        health.last_failed = failed_entries[0].get("timestamp", "")
        health.last_failed_db = failed_entries[0].get("database", "")

    health.total_dbs = len(success_entries) + len(failed_entries)
    health.ok_dbs = len(success_entries)
    health.failed_dbs = len(failed_entries)

    # Check if most recent backup failed
    last = history[-1] if history else {}
    if last.get("status") == "failed":
        health.status = "error"
    elif failed_entries:
        health.status = "warning"
    else:
        health.status = "ok"

    # Try to get remaining disk space on backup drive
    if sys.platform == "win32":
        policy = project.settings.backup
        try:
            import ctypes
            drive = Path(policy.save_path).drive + "\\"
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                drive, None, None, ctypes.pointer(free_bytes)
            )
            health.remaining_gb = round(free_bytes.value / (1024**3), 1)
        except Exception:
            health.remaining_gb = 0.0

    return health


# ═════════════════════════════════════════════════════════════════
#  Cleanup
# ═════════════════════════════════════════════════════════════════

def cleanup_old_backups(project: Project) -> int:
    """Delete .bak files older than retention_days. Returns count deleted."""
    policy = project.settings.backup
    save = Path(policy.save_path)
    if not save.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=policy.retention_days)
    deleted = 0
    for f in save.rglob("*.bak"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


# ═════════════════════════════════════════════════════════════════
#  Backup file browser
# ═════════════════════════════════════════════════════════════════

def get_backup_files(project: Project) -> List[Dict]:
    """Return a flat list of .bak files with metadata."""
    policy = project.settings.backup
    save = Path(policy.save_path)
    if not save.exists():
        return []

    files = []
    for f in sorted(save.rglob("*.bak")):
        try:
            stat = f.stat()
            files.append({
                "path": str(f),
                "name": f.name,
                "size_mb": round(stat.st_size / (1024**2), 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "relative": str(f.relative_to(save)),
            })
        except OSError:
            pass
    return files
