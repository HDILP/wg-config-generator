"""Workspace abstraction — defines which pages and nav items are available per mode."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class NavItem:
    label: str
    icon: str  # Lucide icon name
    page_name: str  # key to route to a method on the app


SERVER_NAV: List[NavItem] = [
    NavItem("仪表盘", "activity", "show_dashboard"),
    NavItem("SQL Server", "database", "show_sql"),
    NavItem("WireGuard", "shield-check", "show_wireguard"),
    NavItem("Windows 防火墙", "shield-alert", "show_firewall"),
    NavItem("自动备份", "hard-drive-upload", "show_backup"),
    NavItem("服务管理", "cpu", "show_services"),
    NavItem("系统信息", "monitor", "show_system_info"),
]

CLIENT_NAV: List[NavItem] = [
    NavItem("项目列表", "folder-tree", "show_projects"),
    NavItem("客户管理", "users", "show_customers"),
    NavItem("WireGuard 配置", "shield-check", "show_wireguard"),
    NavItem("运维信息", "clipboard-list", "show_ops"),
]

BOTH_NAV: List[NavItem] = [
    NavItem("设置", "settings", "show_settings"),
]


def nav_for_mode(mode) -> List[NavItem]:
    if mode.name == "SERVER":
        return SERVER_NAV + BOTH_NAV
    return CLIENT_NAV + BOTH_NAV
