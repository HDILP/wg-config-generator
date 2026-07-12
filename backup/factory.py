"""Backup engine factory — create engines by ID, list available engines."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from backup.engine import BackupEngine
from backup.maintenance_plan import MaintenancePlanEngine
from backup.windows_task import WindowsTaskEngine


_ENGINES: Dict[str, BackupEngine] = {}


def _ensure_loaded() -> None:
    if not _ENGINES:
        _ENGINES["windows_task"] = WindowsTaskEngine()
        _ENGINES["maintenance_plan"] = MaintenancePlanEngine()


def list_engines() -> List[Tuple[str, str]]:
    """Return [(engine_id, display_name), ...]."""
    _ensure_loaded()
    return [(eid, eng.display_name) for eid, eng in _ENGINES.items()]


def get_engine(engine_id: str) -> Optional[BackupEngine]:
    """Get engine by ID, or None if not found."""
    _ensure_loaded()
    return _ENGINES.get(engine_id)


def probe_engines(instance: str) -> List[Tuple[str, str, Optional[str]]]:
    """Probe all engines on target instance.

    Returns [(engine_id, display_name, error_or_None)].
    """
    _ensure_loaded()
    results = []
    for eid, eng in _ENGINES.items():
        err = eng.probe(instance)
        results.append((eid, eng.display_name, err))
    return results


def get_default_engine(instance: str) -> str:
    """Return the first available engine ID, or 'windows_task' as fallback."""
    results = probe_engines(instance)
    for eid, _, err in results:
        if err is None:
            return eid
    return "windows_task"
