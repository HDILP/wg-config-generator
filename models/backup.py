"""Backup config model — per-project backup policy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class BackupPolicy:
    """Single backup policy — one schedule applies to multiple databases.

    Stored in project.json under settings.backup.
    """
    enabled: bool = False
    databases: List[str] = field(default_factory=list)
    schedule_time: str = "02:00"          # HH:MM
    save_path: str = "D:\\SQLBackup"
    retention_days: int = 30
    compression: bool = True              # auto-detected, user can override
    compression_auto_disabled: bool = False  # server doesn't support it
