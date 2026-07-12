"""App — GP Server Manager main application.

Left sidebar + right content area. Page-based navigation.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Dict, Optional

import customtkinter as ctk

from app.theme import apply_theme
from core.project_manager import ProjectManager
from core.wg_keygen import check_wg_available, generate_keypair
from models.project import OpsInfo, Project, ProjectSettings, RemoteInfo, SqlConfig
from pages import (
    BackupCenterPage,
    DashboardPage,
    FirewallPage,
    HomePage,
    OpsInfoPage,
    SettingsPage,
    SQLPage,
    ToolsPage,
    WireGuardPage,
)


class GPServerManager(ctk.CTk):
    """Main application window."""

    WIDTH, HEIGHT = 960, 680

    def __init__(self) -> None:
        super().__init__()
        self.title("GP Server Manager")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(800, 600)

        apply_theme()

        # State
        self._current_project: Optional[Project] = None
        self._current_page: str = ""
        self._pages: Dict[str, ctk.CTkFrame] = {}

        # Check WireGuard
        self._wg_error = check_wg_available()

        # Layout
        self._build_layout()

        # Show start page
        self.show_home()

    # ═══════════════════════════════════════════════════════════════
    #  Layout
    # ═══════════════════════════════════════════════════════════════

    def _build_layout(self) -> None:
        # Outer grid: sidebar | content
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

        # Brand
        ctk.CTkLabel(
            self._sidebar, text="GP Server Manager",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 4))

        # Separator
        ctk.CTkLabel(self._sidebar, text="", height=2,
                     fg_color="#CAC4D0").pack(fill="x", padx=16, pady=(0, 12))

        # Home button
        self._nav_home = ctk.CTkButton(
            self._sidebar, text="🏠  首页",
            font=ctk.CTkFont(size=13),
            fg_color="transparent", text_color="#49454F",
            hover_color="#F3EDF7", anchor="w",
            corner_radius=8, height=36,
            command=self.show_home,
        )
        self._nav_home.pack(fill="x", padx=12, pady=2)

        # Project section (only visible when a project is open)
        self._nav_section = ctk.CTkLabel(
            self._sidebar, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#79747E", anchor="w",
        )
        self._nav_section.pack(fill="x", padx=16, pady=(8, 2))

        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("仪表盘", "📊", "show_dashboard"),
            ("备份中心", "💾", "show_backup"),
            ("WireGuard", "🔒", "show_wireguard"),
            ("SQL Server", "🗄", "show_sql"),
            ("防火墙", "🛡", "show_firewall"),
            ("客户管理", "👥", "show_wireguard"),  # same as WireGuard page
            ("运维信息", "📋", "show_ops"),
            ("工具箱", "🔧", "show_tools"),
        ]

        for label, icon, method_name in nav_items:
            btn = ctk.CTkButton(
                self._sidebar, text=f"{icon}  {label}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", text_color="#49454F",
                hover_color="#F3EDF7", anchor="w",
                corner_radius=8, height=30,
                command=lambda m=method_name: self._nav_to(m),
            )
            btn.pack(fill="x", padx=12, pady=1)
            self._nav_buttons[label] = btn

        # Initially hide project nav
        self._set_sidebar_project(False)

        # Bottom: settings + project list shortcut
        ctk.CTkLabel(self._sidebar, text="", height=2,
                     fg_color="#CAC4D0").pack(fill="x", padx=16, pady=(8, 8))

        ctk.CTkButton(
            self._sidebar, text="⚙  设置",
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color="#49454F",
            hover_color="#F3EDF7", anchor="w",
            corner_radius=8, height=30,
            command=self.show_settings,
        ).pack(fill="x", padx=12, pady=1)

        # Status bar at bottom of sidebar
        self._sidebar_status = ctk.CTkLabel(
            self._sidebar, text="", font=ctk.CTkFont(size=10),
            text_color="#79747E",
        )
        self._sidebar_status.pack(side="bottom", pady=(0, 12))

    def _set_sidebar_project(self, visible: bool) -> None:
        state = "normal" if visible else "hidden"
        for btn in self._nav_buttons.values():
            btn.pack_forget() if not visible else btn.pack(fill="x", padx=12, pady=1)
        if visible:
            for btn in self._nav_buttons.values():
                btn.pack(fill="x", padx=12, pady=1)

    def _nav_to(self, method_name: str) -> None:
        handler = getattr(self, method_name, None)
        if handler:
            handler()

    # ═══════════════════════════════════════════════════════════════
    #  Page switching
    # ═══════════════════════════════════════════════════════════════

    def _switch_to(self, page_class, *args, **kwargs) -> ctk.CTkFrame:
        for w in self._content.winfo_children():
            w.destroy()
        page = page_class(self._content, *args, **kwargs)
        page.pack(fill="both", expand=True)
        return page

    # ═══════════════════════════════════════════════════════════════
    #  Navigation methods
    # ═══════════════════════════════════════════════════════════════

    def show_home(self) -> None:
        self._current_project = None
        self._current_page = "home"
        self._nav_section.configure(text="")
        self._set_sidebar_project(False)
        self._update_nav("首页")

        self._nav_home.configure(fg_color="#EADDFF", text_color="#1C1B1F")
        self._switch_to(HomePage, self)
        self._sidebar_status.configure(text="")

    def show_project_list(self) -> None:
        """Show project list from home page."""
        pnames = ProjectManager.list_projects()
        if not pnames:
            messagebox.showinfo("提示", "还没有项目，先新建一个吧")
            self.show_home()
            return

        # Simple selection dialog via the content area
        from pages.home_page import HomePage
        self._switch_to(HomePage, self)
        # The home page already has the list; we just show it
        self.show_home()

    def show_new_project(self) -> None:
        """Show new project creation dialog."""
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
                self.after(0, lambda: self._open_project(project))
            except Exception as exc:
                self.after(0, lambda: (
                    messagebox.showerror("错误", str(exc)),
                    self._sidebar_status.configure(text=""),
                ))

        threading.Thread(target=_create, daemon=True).start()

    def show_settings(self) -> None:
        self._current_project = None
        self._current_page = "settings"
        self._nav_section.configure(text="")
        self._set_sidebar_project(False)
        self._update_nav("")
        self._switch_to(SettingsPage, self)

    def show_dashboard(self) -> None:
        if not self._current_project:
            messagebox.showwarning("提示", "请先打开一个项目")
            return
        self._current_page = "dashboard"
        self._sidebar_status.configure(
            text=self._current_project.settings.name
        )
        self._switch_to(DashboardPage, self, self._current_project)

    def show_wireguard(self) -> None:
        if not self._current_project:
            return
        self._current_page = "wireguard"
        self._switch_to(WireGuardPage, self, self._current_project)

    def show_sql(self) -> None:
        if not self._current_project:
            return
        self._current_page = "sql"
        self._switch_to(SQLPage, self, self._current_project)

    def show_firewall(self) -> None:
        if not self._current_project:
            return
        self._current_page = "firewall"
        self._switch_to(FirewallPage, self, self._current_project)

    def show_backup(self) -> None:
        if not self._current_project:
            return
        self._current_page = "backup"
        self._switch_to(BackupCenterPage, self, self._current_project)

    def show_ops(self) -> None:
        if not self._current_project:
            return
        self._current_page = "ops"
        self._switch_to(OpsInfoPage, self, self._current_project)

    def show_tools(self) -> None:
        if not self._current_project:
            return
        self._current_page = "tools"
        self._switch_to(ToolsPage, self, self._current_project)

    def set_status(self, text: str) -> None:
        self._sidebar_status.configure(text=text)

    def _update_nav(self, active: str) -> None:
        """Highlight the active nav button."""
        for label, btn in self._nav_buttons.items():
            btn.configure(fg_color="transparent", text_color="#49454F")
        self._nav_home.configure(
            fg_color="#EADDFF" if active == "首页" else "transparent",
            text_color="#1C1B1F" if active == "首页" else "#49454F",
        )

    # ═══════════════════════════════════════════════════════════════
    #  Project lifecycle
    # ═══════════════════════════════════════════════════════════════

    def open_project(self, name: str) -> None:
        try:
            project = ProjectManager.load(name)
            self._open_project(project)
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开项目: {exc}")

    def _open_project(self, project: Project) -> None:
        self._current_project = project
        self._nav_section.configure(text=f"📌  {project.name}")
        self._set_sidebar_project(True)
        self._update_nav("")
        self._sidebar_status.configure(text=project.settings.name)
        self.show_dashboard()


class _NewProjectDialog(ctk.CTkToplevel):
    """Dialog for creating a new project."""

    def __init__(self, parent: GPServerManager):
        super().__init__(parent)
        self.title("新建服务器")
        self.geometry("440x440")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="新建服务器项目",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     ).pack(pady=(16, 12))

        fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        fields_frame.pack(fill="x", padx=20)

        self._entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}

        for label, key, default, options in [
            ("项目名称", "name", "", None),
            ("公网 IP", "ip", "", None),
            ("远程类型", "remote_type", "Sunlogin", ["Sunlogin", "ToDesk", "RustDesk", "Aishu", "Other"]),
            ("远程号码", "remote_id", "", None),
            ("Listen Port", "port", "51820", None),
            ("Server VPN IP", "vpn_ip", "10.66.66.1", None),
            ("Subnet", "subnet", "10.66.66.0/24", None),
        ]:
            ctk.CTkLabel(fields_frame, text=label,
                         font=ctk.CTkFont(size=12),
                         anchor="w").pack(fill="x", pady=(8, 2))
            if options:
                var = ctk.StringVar(value=default)
                w = ctk.CTkOptionMenu(fields_frame, values=options,
                                       variable=var, font=ctk.CTkFont(size=12))
            else:
                w = ctk.CTkEntry(fields_frame, font=ctk.CTkFont(size=12))
                if default:
                    w.insert(0, default)
            w.pack(fill="x", pady=(0, 2))
            self._entries[key] = w

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
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
