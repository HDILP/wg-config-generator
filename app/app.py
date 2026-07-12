"""App — GP Server Manager main application.

Workspace-aware: shows different sidebar + pages based on Server/Client mode.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Dict, Optional, Type

import customtkinter as ctk

from app.theme import apply_theme
from app.workspace import WorkspaceMode, nav_for_mode, NavItem
from core.project_manager import ProjectManager
from core.wg_keygen import check_wg_available
from models.app_settings import AppSettings
from models.project import Project
from pages import (
    BackupCenterPage,
    ClientDashboardPage,
    CustomersPage,
    FirewallPage,
    OpsInfoPage,
    ProjectsPage,
    ServerDashboardPage,
    SettingsPage,
    SQLPage,
    SystemInfoPage,
    WireGuardClientPage,
    WireGuardServerPage,
)


class GPServerManager(ctk.CTk):
    """Main application window — workspace-aware."""

    WIDTH, HEIGHT = 960, 680

    def __init__(self, workspace: WorkspaceMode, settings: AppSettings):
        super().__init__()
        self.title("GP Server Manager")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(800, 600)

        apply_theme()

        # State
        self._workspace = workspace
        self._settings = settings
        self._current_project: Optional[Project] = None
        self._current_page: str = ""
        self._sidebar_buttons: Dict[str, ctk.CTkButton] = {}

        # Check WireGuard
        self._wg_error = check_wg_available()

        # Layout
        self._build_layout()

        # Show start page
        if self._wg_error and workspace == WorkspaceMode.SERVER:
            self._show_wg_error()
        else:
            self._nav_to_home()

    @property
    def workspace(self) -> WorkspaceMode:
        return self._workspace

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def _show_wg_error(self) -> None:
        frame = ctk.CTkFrame(self._content, corner_radius=0, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        ctk.CTkLabel(frame, text="⚠️ WireGuard 未安装",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(60, 10))
        ctk.CTkLabel(frame, text=self._wg_error or "", wraplength=400,
                     font=ctk.CTkFont(size=13), text_color="gray40").pack(pady=10)
        installer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wireguard-installer.exe")
        if os.path.exists(installer):
            ctk.CTkButton(frame, text="⚡ 一键安装 WireGuard",
                          font=ctk.CTkFont(size=14, weight="bold"),
                          command=lambda: subprocess.Popen([installer], shell=True),
                          ).pack(pady=12)
        ctk.CTkButton(frame, text="重启程序", font=ctk.CTkFont(size=13),
                      command=lambda: os.execl(sys.executable, sys.executable, *sys.argv),
                      fg_color="gray40").pack()

    # ═══════════════════════════════════════════════════════════════
    #  Layout
    # ═══════════════════════════════════════════════════════════════

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self._sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self._sidebar.grid(row=0, column=0, sticky="nswe")
        self._sidebar.grid_propagate(False)

        # Content area
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nswe")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

    def _build_sidebar(self) -> None:
        for w in self._sidebar.winfo_children():
            w.destroy()
        self._sidebar_buttons.clear()

        # Brand + workspace badge
        mode_label = {
            WorkspaceMode.SERVER: "🖥 Server",
            WorkspaceMode.CLIENT: "💻 Client",
        }.get(self._workspace, "")

        ctk.CTkLabel(
            self._sidebar, text="GP Server Manager",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 2))
        ctk.CTkLabel(
            self._sidebar, text=mode_label,
            font=ctk.CTkFont(size=10),
            text_color="#79747E",
        ).pack(pady=(0, 8))

        # Separator
        ctk.CTkLabel(self._sidebar, text="", height=2,
                     fg_color="#CAC4D0").pack(fill="x", padx=16, pady=(0, 8))

        # Nav items from workspace
        items = nav_for_mode(self._workspace)
        for item in items:
            btn = ctk.CTkButton(
                self._sidebar, text=f"{item.icon}  {item.label}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", text_color="#49454F",
                hover_color="#F3EDF7", anchor="w",
                corner_radius=8, height=30,
                command=lambda pn=item.page_name: self._nav_to(pn),
            )
            btn.pack(fill="x", padx=12, pady=1)
            self._sidebar_buttons[item.page_name] = btn

        # Separator
        ctk.CTkLabel(self._sidebar, text="", height=2,
                     fg_color="#CAC4D0").pack(fill="x", padx=16, pady=(8, 8))

        # Settings (always at bottom of nav section)
        ctk.CTkButton(
            self._sidebar, text="⚙  设置",
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color="#49454F",
            hover_color="#F3EDF7", anchor="w",
            corner_radius=8, height=30,
            command=self.show_settings,
        ).pack(fill="x", padx=12, pady=1)

        # Status bar at bottom
        self._sidebar_status = ctk.CTkLabel(
            self._sidebar, text="", font=ctk.CTkFont(size=10),
            text_color="#79747E",
        )
        self._sidebar_status.pack(side="bottom", pady=(0, 12))

    def _nav_to(self, page_name: str) -> None:
        handler = getattr(self, page_name, None)
        if handler:
            handler()

    def _update_nav(self, active: str = "") -> None:
        for name, btn in self._sidebar_buttons.items():
            is_active = name == active
            btn.configure(
                fg_color="#EADDFF" if is_active else "transparent",
                text_color="#1C1B1F" if is_active else "#49454F",
            )

    # ═══════════════════════════════════════════════════════════════
    #  Page switching
    # ═══════════════════════════════════════════════════════════════

    def _switch_to(self, page_class: Type[ctk.CTkFrame], *args, **kwargs) -> ctk.CTkFrame:
        """Clear content and show a new page."""
        # Check workspace compatibility
        ws = getattr(page_class, "WORKSPACE", WorkspaceMode.BOTH)
        if ws not in (WorkspaceMode.BOTH, self._workspace):
            messagebox.showwarning(
                "不可用",
                f"该页面在 {self._workspace.value.title()} Mode 下不可用",
            )
            # Return an empty frame to avoid crash
            empty = ctk.CTkFrame(self._content, fg_color="transparent")
            empty.pack(fill="both", expand=True)
            return empty

        for w in self._content.winfo_children():
            w.destroy()
        page = page_class(self._content, *args, **kwargs)
        page.pack(fill="both", expand=True)
        return page

    def set_status(self, text: str) -> None:
        self._sidebar_status.configure(text=text)

    def _nav_to_home(self) -> None:
        if self._workspace == WorkspaceMode.SERVER:
            self.show_server_dashboard()
        else:
            self.show_projects()

    # ═══════════════════════════════════════════════════════════════
    #  Server Mode navigation
    # ═══════════════════════════════════════════════════════════════

    def show_dashboard(self) -> None:
        self._current_page = "show_dashboard"
        self._update_nav("show_dashboard")
        if self._workspace == WorkspaceMode.SERVER:
            self._switch_to(ServerDashboardPage, self)
            self._sidebar_status.configure(text="")
        else:
            self._switch_to(ClientDashboardPage, self)

    def show_sql(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_sql"
        self._update_nav("show_sql")
        self._switch_to(SQLPage, self)

    def show_wireguard(self) -> None:
        self._current_page = "show_wireguard"
        self._update_nav("show_wireguard")
        if self._workspace == WorkspaceMode.SERVER:
            self._switch_to(WireGuardServerPage, self)
        else:
            self._switch_to(WireGuardClientPage, self)

    def show_firewall(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_firewall"
        self._update_nav("show_firewall")
        self._switch_to(FirewallPage, self)

    def show_backup(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_backup"
        self._update_nav("show_backup")
        self._switch_to(BackupCenterPage, self)

    def show_services(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_services"
        self._update_nav("show_services")
        self._switch_to(SystemInfoPage, self, tab="services")

    def show_system_info(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_system_info"
        self._update_nav("show_system_info")
        self._switch_to(SystemInfoPage, self, tab="system")

    # ═══════════════════════════════════════════════════════════════
    #  Client Mode navigation
    # ═══════════════════════════════════════════════════════════════

    def show_projects(self) -> None:
        if self._workspace != WorkspaceMode.CLIENT:
            return
        self._current_project = None
        self._current_page = "show_projects"
        self._update_nav("show_projects")
        self._switch_to(ProjectsPage, self)

    def show_customers(self) -> None:
        if self._workspace != WorkspaceMode.CLIENT:
            return
        self._current_page = "show_customers"
        self._update_nav("show_customers")
        self._switch_to(CustomersPage, self)

    def show_ops(self) -> None:
        if self._workspace != WorkspaceMode.CLIENT:
            return
        if not self._current_project:
            messagebox.showwarning("提示", "请先选择一个项目")
            return
        self._current_page = "show_ops"
        self._update_nav("show_ops")
        self._switch_to(OpsInfoPage, self, self._current_project)

    # ═══════════════════════════════════════════════════════════════
    #  Shared pages
    # ═══════════════════════════════════════════════════════════════

    def show_settings(self) -> None:
        self._current_project = None
        self._current_page = "show_settings"
        self._update_nav("")
        self._switch_to(SettingsPage, self, self._settings, self._workspace)

    # ═══════════════════════════════════════════════════════════════
    #  Project lifecycle (Client Mode)
    # ═══════════════════════════════════════════════════════════════

    def open_project(self, name: str) -> None:
        try:
            project = ProjectManager.load(name)
            self._current_project = project
            self._sidebar_status.configure(text=project.settings.name)
            self.show_dashboard()
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开项目: {exc}")

    def show_new_project(self) -> None:
        dlg = _NewProjectDialog(self)
        self.wait_window(dlg)
        result = dlg.result()
        if result is None:
            return

        name, ip, port, vpn_ip, subnet, remote_type, remote_id = result
        self._sidebar_status.configure(text="Creating project…")

        def _create() -> None:
            try:
                project = ProjectManager.create(
                    name=name, public_ip=ip, listen_port=port,
                    vpn_ip=vpn_ip, subnet=subnet,
                    remote_type=remote_type, remote_id=remote_id,
                )
                self.after(0, lambda: self.open_project(project.name))
            except Exception as exc:
                self.after(0, lambda: (
                    messagebox.showerror("错误", str(exc)),
                    self._sidebar_status.configure(text=""),
                ))

        threading.Thread(target=_create, daemon=True).start()

    def get_current_project(self) -> Optional[Project]:
        return self._current_project

    def open_project_from_list(self, name: str) -> None:
        """Called from ProjectsPage when user clicks a project."""
        self.open_project(name)


class _NewProjectDialog(ctk.CTkToplevel):
    """Dialog for creating a new project."""
    # Kept from original — unchanged
    def __init__(self, parent: GPServerManager):
        super().__init__(parent)
        self.title("新建服务器")
        self.geometry("440x520")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="新建服务器项目",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     ).pack(pady=(16, 12))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=0,
                                         fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)

        self._entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}

        for label, key, default, options in [
            ("项目名称", "name", "", None),
            ("公网 IP", "ip", "", None),
            ("远程类型", "remote_type", "帮我吧", ["帮我吧", "向日葵", "ToDesk", "RustDesk", "Other"]),
            ("远程号码", "remote_id", "", None),
            ("Listen Port", "port", "51820", None),
            ("Server VPN IP", "vpn_ip", "10.66.66.1", None),
            ("Subnet", "subnet", "10.66.66.0/24", None),
        ]:
            ctk.CTkLabel(scroll, text=label,
                         font=ctk.CTkFont(size=12),
                         anchor="w").pack(fill="x", pady=(8, 2))
            if options:
                var = ctk.StringVar(value=default)
                w = ctk.CTkOptionMenu(scroll, values=options,
                                       variable=var, font=ctk.CTkFont(size=12))
            else:
                w = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=12))
                if default:
                    w.insert(0, default)
            w.pack(fill="x", pady=(0, 2))
            self._entries[key] = w

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(pady=(20, 12))
        ctk.CTkButton(btn_frame, text="取消", width=100,
                       command=self.destroy,
                       font=ctk.CTkFont(size=13),
                       ).pack(side="left", padx=(0, 12))
        self._create_btn = ctk.CTkButton(
            btn_frame, text="创建", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._confirm,
        )
        self._create_btn.pack(side="right")

        self._confirmed = False
        self._result: tuple = ()

    def _confirm(self) -> None:
        name = self._entries["name"].get().strip()
        ip = self._entries["ip"].get().strip()
        if not name:
            messagebox.showwarning("验证", "项目名称不能为空", parent=self)
            return
        try:
            port = int(self._entries["port"].get().strip() or "51820")
        except ValueError:
            messagebox.showwarning("验证", "端口必须是数字", parent=self)
            return

        self._confirmed = True
        self._result = (
            name, ip, port,
            self._entries["vpn_ip"].get().strip() or "10.66.66.1",
            self._entries["subnet"].get().strip() or "10.66.66.0/24",
            self._entries["remote_type"].get(),
            self._entries["remote_id"].get().strip(),
        )
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None
