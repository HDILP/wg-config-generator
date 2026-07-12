"""Pages package — all UI pages for GP Server Manager.

Each page declares WORKSPACE to control which mode it appears in.
- WorkspaceMode.SERVER: only in Server Mode
- WorkspaceMode.CLIENT: only in Client Mode
- WorkspaceMode.BOTH (or unset): both modes
"""
from pages.backup_page import BackupCenterPage
from pages.client_dashboard_page import ClientDashboardPage
from pages.customers_page import CustomersPage
from pages.firewall_page import FirewallPage
from pages.ops_page import OpsInfoPage
from pages.projects_page import ProjectsPage
from pages.server_dashboard_page import ServerDashboardPage
from pages.settings_page import SettingsPage
from pages.sql_page import SQLPage
from pages.system_info_page import SystemInfoPage
from pages.wireguard_client_page import WireGuardClientPage
from pages.wireguard_server_page import WireGuardServerPage

__all__ = [
    "BackupCenterPage",
    "ClientDashboardPage",
    "CustomersPage",
    "FirewallPage",
    "OpsInfoPage",
    "ProjectsPage",
    "ServerDashboardPage",
    "SettingsPage",
    "SQLPage",
    "SystemInfoPage",
    "WireGuardClientPage",
    "WireGuardServerPage",
]
