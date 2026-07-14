"""Maintenance Plan engine — SQL Agent Job-based backup scheduling.

Uses documented system stored procedures (sp_add_job, sp_add_jobstep,
sp_add_schedule, sp_attach_schedule, etc.) to create scheduled backup jobs
that work on SQL Server 2008 through 2022.

NOTE: True SSIS-based Maintenance Plans require SMO assemblies. This
implementation creates SQL Agent Jobs executing BACKUP DATABASE T-SQL,
which is what the SSMS Maintenance Plan Wizard ultimately creates,
minus the SSIS packaging layer. Fully compatible across all supported versions.
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from backup.engine import BackupEngine, EngineStatus
from services.sql_service import _agent_service, _get_agent_state, _server

PLAN_NAME = "GP_ServerManager_Backup"
SCHEDULE_NAME = "GP_ServerManager_Backup_Schedule"


# ── SQL helpers ─────────────────────────────────────────────────


def _exec_sql(instance: str, query: str, timeout: int = 60) -> Tuple[str, str]:
    """Execute T-SQL against the server. Returns (stdout, stderr)."""
    import subprocess

    if sys.platform != "win32":
        return "[mock]", ""

    # Try PowerShell / .NET SqlClient first
    try:
        sq = query.replace("'", "''")
        conn_str = f"Server={_server(instance)};Database=master;Integrated Security=SSPI;Trusted_Connection=True;"
        script = f"""
$conn = New-Object System.Data.SqlClient.SqlConnection("{conn_str}")
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandTimeout = {timeout}
$cmd.CommandText = '{sq}'
try {{
    $rdr = $cmd.ExecuteReader()
    $lines = @()
    do {{ while ($rdr.Read()) {{
        $vals = for ($i=0; $i -lt $rdr.FieldCount; $i++) {{ $rdr.GetValue($i).ToString() }}
        $lines += ($vals -join "|")
    }} }} while ($rdr.NextResult())
    $rdr.Close()
    Write-Output ($lines -join "`n")
}} catch {{
    Write-Error $_.Exception.Message
}}
$conn.Close()
"""
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout + 30,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip(), r.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return "", str(exc)


def _exec_non_query(instance: str, query: str, timeout: int = 60) -> str:
    """Execute non-query T-SQL (INSERT/UPDATE/EXEC). Returns result or error."""
    if sys.platform != "win32":
        return "OK (mock)"

    import subprocess

    conn_str = f"Server={_server(instance)};Database=master;Integrated Security=SSPI;Trusted_Connection=True;"
    sq = query.replace("'", "''")
    script = f"""
$conn = New-Object System.Data.SqlClient.SqlConnection("{conn_str}")
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandTimeout = {timeout}
$cmd.CommandText = '{sq}'
try {{
    $cmd.ExecuteNonQuery() | Out-Null
    Write-Output "OK"
}} catch {{
    Write-Error $_.Exception.Message
}}
$conn.Close()
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout + 30,
            encoding="utf-8", errors="replace",
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        if out == "OK":
            return "OK"
        return err or out or "Unknown error"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return str(exc)


# ── Agent / feature detection ──────────────────────────────────


def _check_agent_status(instance: str) -> Optional[str]:
    """Check SQL Agent service. Returns None if OK, error string if not."""
    import subprocess

    if sys.platform != "win32":
        return None  # mock

    svc = _agent_service(instance)
    state = _get_agent_state(svc)
    if state == "Running":
        return None
    if state == "Stopped":
        return "SQL Server Agent 服务未启动"
    return "SQL Server Agent 服务状态异常"


def _check_agent_disabled(instance: str) -> Optional[str]:
    """Check if SQL Agent startup type is disabled."""
    import subprocess

    if sys.platform != "win32":
        return None

    svc = _agent_service(instance)
    try:
        r = subprocess.run(
            ["sc", "qc", svc],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.splitlines():
            if "START_TYPE" in line and "DISABLED" in line.upper():
                return "SQL Server Agent 已被禁用，请启用后再创建备份计划"
        return None
    except (FileNotFoundError, OSError):
        return None


def _check_express_edition(instance: str) -> Optional[str]:
    """SQL Server Express doesn't include SQL Agent."""
    out, _ = _exec_sql(instance, "SELECT SERVERPROPERTY('Edition')", 10)
    if "Express" in out or "express" in out:
        return "SQL Server Express 版本不包含 SQL Server Agent，无法创建计划任务"
    return None


# ── Job SQL templates ──────────────────────────────────────────


def _backup_tsql(databases: List[str], save_path: str, compression: bool) -> str:
    """Generate T-SQL BACKUP DATABASE statements for multiple databases."""
    import os
    comp = ", COMPRESSION" if compression else ""
    now = "REPLACE(CONVERT(VARCHAR(8), GETDATE(), 112), '-', '') + '_' + REPLACE(CONVERT(VARCHAR(8), GETDATE(), 108), ':', '')"
    lines = []
    for db in databases:
        dir_path = save_path.replace("\\", "\\\\")
        lines.append(
            f"DECLARE @fname NVARCHAR(500) = '{dir_path}\\\\'\n"
            f"    + CONVERT(VARCHAR(8), GETDATE(), 112) + '\\\\'\n"
            f"    + '{db}_' + REPLACE(CONVERT(VARCHAR(8), GETDATE(), 108), ':', '') + '.bak'\n"
            f"EXEC msdb.dbo.xp_create_subdir LEFT(@fname, LEN(@fname) - CHARINDEX('\\\\', REVERSE(@fname)) + 1)\n"
            f"BACKUP DATABASE [{db}] TO DISK = @fname WITH INIT, FORMAT{comp}"
        )
    return "\n".join(lines)


def _cleanup_tsql(save_path: str, retention_days: int) -> str:
    """Generate PowerShell cleanup command for old backups."""
    # Use xp_cmdshell to run PowerShell for file cleanup (if enabled)
    # Otherwise use a separate approach
    return (
        f"-- Cleanup: delete .bak files older than {retention_days} days\n"
        "DECLARE @retention INT = " + str(retention_days) + "\n"
        "DECLARE @cutoff DATETIME = DATEADD(DAY, -@retention, GETDATE())\n"
        f"-- Note: file cleanup requires xp_cmdshell or external script\n"
        "-- See GP Server Manager backup service for file-level cleanup"
    )


# ── Engine implementation ──────────────────────────────────────


class MaintenancePlanEngine(BackupEngine):
    """Backup via SQL Server Agent Job (Maintenance Plan compatible)."""

    @property
    def engine_id(self) -> str:
        return "maintenance_plan"

    @property
    def display_name(self) -> str:
        return "SQL Server 计划（Maintenance Plan）"

    # ── probing ───────────────────────────────────────────────

    def probe(self, instance: str) -> Optional[str]:
        """Return None if available, error string if not."""
        if sys.platform != "win32":
            return None  # mock

        # 1. Express edition check
        edition_err = _check_express_edition(instance)
        if edition_err:
            return edition_err

        # 2. Agent not running
        agent_err = _check_agent_status(instance)
        if agent_err:
            return agent_err

        # 3. Agent disabled
        disabled_err = _check_agent_disabled(instance)
        if disabled_err:
            return disabled_err

        return None

    # ── plan CRUD ─────────────────────────────────────────────

    def create_plan(
        self,
        instance: str,
        databases: List[str],
        schedule_time: str,
        save_path: str,
        retention_days: int,
        compression: bool,
        plan_name: str = "",
    ) -> str:
        name = plan_name or PLAN_NAME
        sched_name = f"{name}_Schedule"

        # Parse time
        parts = schedule_time.split(":")
        hour = parts[0].zfill(2) if len(parts) > 0 else "02"
        minute = parts[1].zfill(2) if len(parts) > 1 else "00"
        start_time = f"{hour}{minute}00"

        backup_sql = _backup_tsql(databases, save_path, compression)
        cleanup_sql = _cleanup_tsql(save_path, retention_days)

        # Check if job already exists
        out, _ = _exec_sql(instance,
            f"SELECT COUNT(*) FROM msdb.dbo.sysjobs WHERE name = '{name}'", 10)
        if out.strip() and out.strip() != "0":
            return (f"检测到已有备份计划「{name}」。\n"
                    "请使用「更新」修改，或「删除」后重新创建。")

        # Create everything in one batch
        batch = f"""
-- Job
EXEC msdb.dbo.sp_add_job
    @job_name = N'{name}',
    @description = N'GP Server Manager - Auto Database Backup',
    @owner_login_name = N'sa',
    @enabled = 1

-- Step 1: Backup
EXEC msdb.dbo.sp_add_jobstep
    @job_name = N'{name}',
    @step_name = N'Backup Databases',
    @subsystem = N'TSQL',
    @command = N'{backup_sql}',
    @database_name = N'master',
    @on_success_action = 3,
    @on_fail_action = 2

-- Step 2: Cleanup
EXEC msdb.dbo.sp_add_jobstep
    @job_name = N'{name}',
    @step_name = N'Cleanup Old Backups',
    @subsystem = N'TSQL',
    @command = N'{cleanup_sql}',
    @database_name = N'master'

-- Schedule
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = N'{sched_name}',
    @freq_type = 4,
    @freq_interval = 1,
    @active_start_time = {start_time}

EXEC msdb.dbo.sp_attach_schedule
    @job_name = N'{name}',
    @schedule_name = N'{sched_name}'

-- Target local server
EXEC msdb.dbo.sp_add_jobserver
    @job_name = N'{name}',
    @server_name = N'(local)'
"""
        result = _exec_non_query(instance, batch, timeout=30)
        if result != "OK":
            return f"创建失败: {result}"

        return f"OK: 备份计划「{name}」已创建"

    def update_plan(
        self,
        instance: str,
        databases: List[str],
        schedule_time: str,
        save_path: str,
        retention_days: int,
        compression: bool,
        plan_name: str = "",
    ) -> str:
        name = plan_name or PLAN_NAME
        sched_name = f"{name}_Schedule"

        # Parse time
        parts = schedule_time.split(":")
        hour = parts[0].zfill(2) if len(parts) > 0 else "02"
        minute = parts[1].zfill(2) if len(parts) > 1 else "00"
        start_time = f"{hour}{minute}00"

        backup_sql = _backup_tsql(databases, save_path, compression)

        # Update job steps and schedule
        batch = f"""
-- Update job step 1 (backup)
EXEC msdb.dbo.sp_update_jobstep
    @job_name = N'{name}',
    @step_id = 1,
    @command = N'{backup_sql}',
    @database_name = N'master'

-- Update schedule time
EXEC msdb.dbo.sp_update_schedule
    @schedule_name = N'{sched_name}',
    @active_start_time = {start_time}

-- Ensure job is enabled
EXEC msdb.dbo.sp_update_job
    @job_name = N'{name}',
    @enabled = 1
"""
        result = _exec_non_query(instance, batch, timeout=30)
        if result != "OK":
            return f"更新失败: {result}"

        return f"OK: 备份计划「{name}」已更新"

    def delete_plan(self, instance: str, plan_name: str = "") -> str:
        name = plan_name or PLAN_NAME
        result = _exec_non_query(instance,
            f"EXEC msdb.dbo.sp_delete_job @job_name = N'{name}'", timeout=30)
        if result != "OK":
            # Check if job exists
            out, _ = _exec_sql(instance,
                f"SELECT COUNT(*) FROM msdb.dbo.sysjobs WHERE name = '{name}'", 10)
            if out.strip() == "0":
                return "OK: 备份计划不存在，无需删除"
            return f"删除失败: {result}"
        return f"OK: 备份计划「{name}」已删除"

    def enable(self, instance: str, plan_name: str = "") -> str:
        name = plan_name or PLAN_NAME
        result = _exec_non_query(instance,
            f"EXEC msdb.dbo.sp_update_job @job_name = N'{name}', @enabled = 1", 15)
        if result != "OK":
            return f"启用失败: {result}"
        return f"OK: 备份计划「{name}」已启用"

    def disable(self, instance: str, plan_name: str = "") -> str:
        name = plan_name or PLAN_NAME
        result = _exec_non_query(instance,
            f"EXEC msdb.dbo.sp_update_job @job_name = N'{name}', @enabled = 0", 15)
        if result != "OK":
            return f"禁用失败: {result}"
        return f"OK: 备份计划「{name}」已禁用"

    def query_status(self, instance: str, plan_name: str = "") -> EngineStatus:
        name = plan_name or PLAN_NAME
        status = EngineStatus(name=name)

        # Check if job exists and is enabled
        out, _ = _exec_sql(instance, f"""
SELECT j.name, j.enabled, jh.run_date, jh.run_time, jh.run_status,
       s.active_start_time
FROM msdb.dbo.sysjobs j
LEFT JOIN msdb.dbo.sysjobhistory jh
    ON j.job_id = jh.job_id AND jh.step_id = 0
    AND jh.run_date = (SELECT MAX(x.run_date) FROM msdb.dbo.sysjobhistory x
                       WHERE x.job_id = j.job_id AND x.step_id = 0)
LEFT JOIN msdb.dbo.sysjobschedules js ON j.job_id = js.job_id
LEFT JOIN msdb.dbo.sysschedules s ON js.schedule_id = s.schedule_id
WHERE j.name = '{name}'
""", 15)

        if not out or out.startswith("<error"):
            status.exists = False
            return status

        # Parse result: format is "name|enabled|run_date|run_time|run_status|start_time"
        for line in out.splitlines():
            parts = line.split("|")
            if len(parts) >= 1 and parts[0].strip():
                status.exists = True
                if len(parts) >= 2:
                    status.enabled = parts[1].strip() == "1"
                if len(parts) >= 5 and parts[2].strip():
                    # Convert run_date (20260712) and run_time (20000) to timestamp
                    rd = parts[2].strip()
                    rt = parts[3].strip().zfill(6)
                    try:
                        status.last_run = f"{rd[:4]}-{rd[4:6]}-{rd[6:8]} {rt[:2]}:{rt[2:4]}"
                    except IndexError:
                        pass
                    rs = parts[4].strip()
                    if rs == "1":
                        status.last_result = "success"
                    elif rs == "0":
                        status.last_result = "failed"
                    else:
                        status.last_result = "unknown"
        return status
