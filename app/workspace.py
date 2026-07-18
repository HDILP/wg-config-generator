"""Workspace abstraction — defines which pages and nav items are available per mode.

NavItem.icon now holds a Lucide icon name (used with utils.icon_loader).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from models.workspace import WorkspaceMode


@dataclass
class NavItem:
    label: str
    icon: str  # Lucide icon name (used with icon_loader)
    page_name: str  # key to route to a method on the app
    section: str = "main"  # "main" | "fold" — for collapsible sidebar groups
    project_required: bool = False  # Client mode: only show when project is open


SERVER_NAV: List[NavItem] = [
    NavItem("仪表盘", "layout-dashboard", "show_dashboard"),
    NavItem("SQL Server", "database", "show_sql"),
    NavItem("WireGuard", "lock", "show_wireguard"),
    NavItem("防火墙", "shield", "show_firewall"),
    NavItem("备份", "hard-drive", "show_backup"),
    NavItem("系统信息", "activity", "show_system_info", section="fold"),
]

CLIENT_NAV: List[NavItem] = [
    NavItem("仪表盘", "layout-dashboard", "show_dashboard"),
    NavItem("项目", "folder-open", "show_projects"),
    NavItem("客户", "users", "show_customers", project_required=True),
    NavItem("WireGuard", "lock", "show_wireguard", project_required=True),
    # ops merged into dashboard per grill decision
    # deploy merged into wireguard per grill decision
]

BOTH_NAV: List[NavItem] = [
    NavItem("设置", "settings", "show_settings", section="main"),
]


def nav_for_mode(mode: WorkspaceMode) -> List[NavItem]:
    if mode == WorkspaceMode.SERVER:
        return SERVER_NAV + BOTH_NAV
    return CLIENT_NAV + BOTH_NAV


def nav_by_section(items: List[NavItem]) -> dict[str, List[NavItem]]:
    """Group NavItems by section for sidebar rendering."""
    groups: dict[str, List[NavItem]] = {}
    for item in items:
        groups.setdefault(item.section, []).append(item)
    return groups
