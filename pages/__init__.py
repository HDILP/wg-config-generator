"""Pages package — all UI pages for GP Server Manager.

Import pages by name to use as app navigation targets.
Pages are CTkFrame subclasses that receive the main app reference.
"""
from pages.backup_page import BackupCenterPage
from pages.dashboard_page import DashboardPage
from pages.firewall_page import FirewallPage
from pages.home_page import HomePage
from pages.ops_page import OpsInfoPage
from pages.settings_page import SettingsPage
from pages.sql_page import SQLPage
from pages.tools_page import ToolsPage
from pages.wireguard_page import WireGuardPage

__all__ = [
    "BackupCenterPage",
    "DashboardPage",
    "FirewallPage",
    "HomePage",
    "OpsInfoPage",
    "SettingsPage",
    "SQLPage",
    "ToolsPage",
    "WireGuardPage",
]
