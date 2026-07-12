"""Windows Task Scheduler backup engine — adapter wrapping existing services."""
from __future__ import annotations

import sys
from typing import List, Optional

from backup.engine import BackupEngine, EngineStatus
from models.project import Project
from services.backup_service import (
    create_scheduled_task,
    get_scheduled_task_status,
    remove_scheduled_task,
)


class WindowsTaskEngine(BackupEngine):
    """Backup via Windows Task Scheduler (schtasks.exe).

    Wraps the existing implementation in services/backup_service.py.
    """

    @property
    def engine_id(self) -> str:
        return "windows_task"

    @property
    def display_name(self) -> str:
        return "Windows 计划任务"

    def probe(self, instance: str) -> Optional[str]:
        """Windows Task Scheduler is always available on Windows."""
        if sys.platform != "win32":
            return "当前不是 Windows 系统"
        return None

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
        # We need a Project object. Create a minimal one for the scheduler.
        from models.project import BackupPolicy, OpsInfo, Project, ProjectSettings, RemoteInfo, SqlConfig
        from models.keypair import KeyPair

        settings = ProjectSettings(
            name=plan_name or "GP_Backup",
            backup=BackupPolicy(
                enabled=True,
                databases=databases,
                schedule_time=schedule_time,
                save_path=save_path,
                retention_days=retention_days,
                compression=compression,
            ),
            sql=SqlConfig(instance=instance),
        )
        proj = Project(settings=settings, server_keypair=KeyPair())
        return create_scheduled_task(proj)

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
        # Re-create (schtasks /create /f overwrites)
        return self.create_plan(
            instance, databases, schedule_time, save_path,
            retention_days, compression, plan_name,
        )

    def delete_plan(self, instance: str, plan_name: str = "") -> str:
        from models.keypair import KeyPair
        from models.project import Project, ProjectSettings, SqlConfig

        proj = Project(
            settings=ProjectSettings(name=plan_name or "GP_Backup", sql=SqlConfig(instance=instance)),
            server_keypair=KeyPair(),
        )
        return remove_scheduled_task(proj)

    def enable(self, instance: str, plan_name: str = "") -> str:
        # Windows Task Scheduler: we re-create the task (it's already enabled by default)
        return "Windows 计划任务创建时默认启用。请使用 schtasks /change /enable 手动管理。"

    def disable(self, instance: str, plan_name: str = "") -> str:
        return self.delete_plan(instance, plan_name)

    def query_status(self, instance: str, plan_name: str = "") -> EngineStatus:
        from models.keypair import KeyPair
        from models.project import Project, ProjectSettings, SqlConfig

        proj = Project(
            settings=ProjectSettings(name=plan_name or "GP_Backup", sql=SqlConfig(instance=instance)),
            server_keypair=KeyPair(),
        )
        raw = get_scheduled_task_status(proj)
        exists = raw is not None
        return EngineStatus(
            exists=exists,
            enabled=exists,
            name=plan_name or "GP_Backup",
            last_run="",
            next_run="",
            last_result="unknown",
            raw={"task_status": raw or ""},
        )
