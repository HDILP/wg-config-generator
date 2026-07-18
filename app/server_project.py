"""Persistent machine-local profile used by Server Mode."""
from __future__ import annotations

from core.project_manager import ProjectManager
from models.project import Project, ProjectSettings, SqlConfig

LOCAL_SERVER_PROJECT = "__local_server__"


def load_local_server() -> Project:
    """Return Server Mode's profile, creating it without WireGuard keys."""
    try:
        return ProjectManager.load(LOCAL_SERVER_PROJECT)
    except FileNotFoundError:
        project = Project(settings=ProjectSettings(
            name=LOCAL_SERVER_PROJECT, sql=SqlConfig(instance="MSSQLSERVER")))
        ProjectManager.save(project)
        return project
