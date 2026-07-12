"""Backup engines — pluggable backup implementations.

Directory structure:
    engine.py          — ABC
    windows_task.py    — Windows Task Scheduler
    maintenance_plan.py — SQL Server Agent Job
    factory.py         — Engine factory
"""
from backup.engine import BackupEngine, EngineStatus
from backup.factory import get_default_engine, get_engine, list_engines, probe_engines
from backup.maintenance_plan import MaintenancePlanEngine
from backup.windows_task import WindowsTaskEngine

__all__ = [
    "BackupEngine",
    "EngineStatus",
    "WindowsTaskEngine",
    "MaintenancePlanEngine",
    "get_engine",
    "list_engines",
    "probe_engines",
    "get_default_engine",
]
