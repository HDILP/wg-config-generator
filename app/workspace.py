"""Workspace abstraction — defines which pages and nav items are available per mode."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from models.workspace import WorkspaceMode


@dataclass
class NavItem:
    label: str
    icon: str
    page_name: str  # key to route to a method on the app


SERVER_NAV: List[NavItem] = [
    NavItem("仪表盘", "📊", "show_dashboard"),
    NavItem("SQL Server", "🗄", "show_sql"),
    NavItem("WireGuard", "🔒", "show_wireguard"),
    NavItem("Windows 防火墙", "🛡", "show_firewall"),
    NavItem("自动备份", "💾", "show_backup"),
    NavItem("服务管理", "⚙", "show_services"),
    NavItem("系统信息", "🔧", "show_system_info"),
]

CLIENT_NAV: List[NavItem] = [
    NavItem("项目列表", "📁", "show_projects"),
    NavItem("客户管理", "👥", "show_customers"),
    NavItem("WireGuard 配置", "🔒", "show_wireguard"),
    NavItem("运维信息", "📋", "show_ops"),
]

BOTH_NAV: List[NavItem] = [
    NavItem("设置", "⚙", "show_settings"),
]


def nav_for_mode(mode: WorkspaceMode) -> List[NavItem]:
    if mode == WorkspaceMode.SERVER:
        return SERVER_NAV + BOTH_NAV
    return CLIENT_NAV + BOTH_NAV
