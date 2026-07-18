"""BackupEngine — abstract interface for all backup engines.

Each engine implements create/update/delete/enable/disable/query_status.
The UI never talks directly to any engine — always through this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EngineStatus:
    """Standardised status returned by every engine."""
    exists: bool = False
    enabled: bool = False
    name: str = ""
    last_run: str = ""          # human-readable timestamp
    next_run: str = ""          # human-readable timestamp
    last_result: str = ""       # "success" / "failed" / "unknown"
    last_error: str = ""
    raw: Dict = field(default_factory=dict)


class BackupEngine(ABC):
    """Abstract backup engine. Every engine must implement all methods."""

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Unique engine identifier, e.g. 'windows_task', 'maintenance_plan'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in UI."""
        ...

    @abstractmethod
    def probe(self, instance: str) -> Optional[str]:
        """Check if this engine is available on the target server.
        Returns None if available, or an error string describing why not.
        """
        ...

    @abstractmethod
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
        """Create a backup plan. Returns status/result string."""
        ...

    @abstractmethod
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
        """Update an existing backup plan."""
        ...

    @abstractmethod
    def delete_plan(self, instance: str, plan_name: str = "") -> str:
        """Delete the backup plan."""
        ...

    @abstractmethod
    def enable(self, instance: str, plan_name: str = "") -> str:
        """Enable the backup plan."""
        ...

    @abstractmethod
    def disable(self, instance: str, plan_name: str = "") -> str:
        """Disable the backup plan."""
        ...

    @abstractmethod
    def query_status(self, instance: str, plan_name: str = "") -> EngineStatus:
        """Query current status of the backup plan."""
        ...
