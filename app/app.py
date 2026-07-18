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
from typing import Callable, Dict, Optional, Type

import customtkinter as ctk

from app.theme import apply_theme
from app.workspace import WorkspaceMode, NavItem, nav_for_mode, nav_by_section
from core.project_manager import ProjectManager
from core.wg_keygen import check_wg_available
from app.server_project import load_local_server
from models.app_settings import AppSettings
from models.project import Project
from pages import (
    BackupCenterPage,
    ClientDashboardPage,
    CustomersPage,
    FirewallPage,
    ProjectsPage,
    ServerDashboardPage,
    SettingsPage,
    SQLPage,
    SystemInfoPage,
    WireGuardClientPage,
    WireGuardServerPage,
)
from utils.icon_loader import load_icon, clear_cache
from app.theme import C, PAD
from widgets.toast import ToastFrame, ModalConfirm


class GPServerManager(ctk.CTk):
    """Main application window — workspace-aware."""

    WIDTH, HEIGHT = 960, 680

    def __init__(self, workspace: WorkspaceMode, settings: AppSettings):
        super().__init__()
        self.title("GP Server Manager")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(800, 600)
        # Defer icon set past CTk's own init so it doesn't get overwritten
        self.after(0, lambda: self.iconbitmap(
            str(Path(__file__).resolve().parent.parent / "icon.ico")
        ))
        apply_theme()

        # State
        self._workspace = workspace
        self._settings = settings
        self._current_project: Optional[Project] = None
        self._current_page: str = ""
        self._sidebar_buttons: Dict[str, ctk.CTkButton] = {}

        # Check WireGuard
        self._wg_error = check_wg_available()
        self._server_project: Optional[Project] = (
            load_local_server() if workspace == WorkspaceMode.SERVER else None
        )

        # Layout
        self._build_layout()

        # Show start page
        # WireGuard is optional: the other local-server tools stay available.
        self._nav_to_home()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Clean shutdown: stop event loop, destroy, then exit."""
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass
        import os
        os._exit(0)

    def destroy(self) -> None:
        clear_cache()
        super().destroy()

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
        installer = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "assets", "installers", "wireguard-amd64-1.1.msi",
        )
        if os.path.exists(installer):
            ctk.CTkButton(frame, text="⚡ 一键安装 WireGuard",
                          font=ctk.CTkFont(size=14, weight="bold"),
                          command=lambda: subprocess.Popen(
                              ["msiexec.exe", "/i", installer]),
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

        # Sidebar with dedicated bg
        self._sidebar = ctk.CTkFrame(self, width=200, corner_radius=0,
                                     fg_color=C["surface_variant"])
        self._sidebar.grid(row=0, column=0, sticky="nswe")
        self._sidebar.grid_propagate(False)

        # Vertical separator
        sep = ctk.CTkFrame(self, width=1, fg_color=C["outline_variant"])
        sep.grid(row=0, column=0, sticky="ns", padx=(199, 0))

        # Content area
        self._content = ctk.CTkFrame(self, corner_radius=0,
                                     fg_color=C["container_bg"])
        self._content.grid(row=0, column=1, sticky="nswe")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

    def _build_sidebar(self) -> None:
        for w in self._sidebar.winfo_children():
            w.destroy()
        self._sidebar_buttons.clear()
        is_client = self._workspace == WorkspaceMode.CLIENT

        # Brand
        brand_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=PAD["lg"], pady=(PAD["lg"], PAD["sm"]))
        
        app_icon = load_icon("server", size=20, color=C["primary"])
        ctk.CTkLabel(brand_frame, text="", image=app_icon).pack(side="left", padx=(0, PAD["sm"]))
        ctk.CTkLabel(
            brand_frame, text="GP Server",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C["on_surface"],
        ).pack(side="left")
        ctk.CTkLabel(
            brand_frame, text="Manager",
            font=ctk.CTkFont(size=15),
            text_color=C["on_surface_variant"],
        ).pack(side="left")

        mode_label = {
            WorkspaceMode.SERVER: "Server",
            WorkspaceMode.CLIENT: "Client",
        }.get(self._workspace, "")
        ctk.CTkLabel(
            self._sidebar, text=mode_label,
            font=ctk.CTkFont(size=10),
            text_color=C["outline"],
        ).pack(pady=(0, PAD["md"]))

        # Separator (spacing only)
        ctk.CTkLabel(self._sidebar, text="", height=1, fg_color="transparent"
                     ).pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))

        # Build navigation grouped by section
        nav_items = nav_for_mode(self._workspace)
        if is_client and not self._current_project:
            nav_items = [i for i in nav_items if not i.project_required]
        groups = nav_by_section(nav_items)

        # Main section
        for item in groups.get("main", []):
            # Don't render project-required items here (shown in project section below)
            if is_client and self._current_project and item.project_required:
                continue
            self._add_nav_button(item)

        # Project name + sub-items (Client mode with project open)
        if is_client and self._current_project:
            proj_items = [i for i in nav_items if i.project_required]
            if proj_items:
                folder_icon = load_icon("folder-open", size=14, color=C["primary"])
                proj_row = ctk.CTkFrame(self._sidebar, fg_color="transparent")
                proj_row.pack(fill="x", padx=PAD["lg"], pady=(PAD["md"], 0))
                ctk.CTkLabel(proj_row, text="", image=folder_icon).pack(side="left", padx=(0, PAD["sm"]))
                ctk.CTkLabel(
                    proj_row,
                    text=self._current_project.settings.name,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=C["primary"],
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)
                for item in proj_items:
                    self._add_nav_button(item)

        # Fold section (collapsible)
        fold_items = groups.get("fold", [])
        if fold_items:
            self._fold_open = True
            self._fold_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
            self._fold_frame.pack(fill="x", padx=PAD["md"], pady=(PAD["md"], 0))

            self._fold_btn = ctk.CTkButton(
                self._fold_frame, text="",
                image=self._make_fold_icon(),
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent", text_color=C["outline"],
                hover_color=C["surface_variant"],
                width=28, height=24, corner_radius=8,
                command=self._toggle_fold,
            )
            self._fold_btn.pack(anchor="w")

            # Use grid so grid_remove/grid preserves position during toggle
            self._fold_container = ctk.CTkFrame(self._sidebar, fg_color="transparent")
            self._fold_container.pack(fill="x", padx=PAD["md"], pady=(PAD["sm"], 0))

            for item in fold_items:
                self._add_nav_button(item, parent=self._fold_container)
        else:
            self._fold_open = False
            self._fold_frame = None
            self._fold_btn = None
            self._fold_container = None

        # Status bar at bottom
        self._sidebar_status = ctk.CTkLabel(
            self._sidebar, text="", font=ctk.CTkFont(size=10),
            text_color=C["outline"],
        )
        self._sidebar_status.pack(side="bottom", pady=(0, PAD["lg"]))

    def _build_project_switcher(self) -> None:
        """Bottom project switcher dropdown."""
        sep = ctk.CTkLabel(self._sidebar, text="", height=1,
                           fg_color=C["outline_variant"])
        sep.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["sm"]))
        proj_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        proj_frame.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["sm"]))

        icon = load_icon("folder-open", size=14, color=C["primary"])
        ctk.CTkLabel(proj_frame, text="", image=icon,
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, PAD["sm"]))
        ctk.CTkLabel(
            proj_frame,
            text=self._current_project.settings.name,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C["primary"],
        ).pack(side="left", fill="x", expand=True)

        # Quick switch: list recent projects
        from core.project_manager import ProjectManager
        projs = ProjectManager.list_projects()
        if len(projs) > 1:
            ctk.CTkButton(
                proj_frame, text="▼", width=20, height=18,
                font=ctk.CTkFont(size=8),
                fg_color="transparent", text_color=C["outline"],
                hover_color=C["surface_variant"],
                command=self._show_project_menu,
            ).pack(side="right", padx=(PAD["sm"], 0))

    def _show_project_menu(self) -> None:
        """Show a popup menu with recent projects to switch to."""
        from core.project_manager import ProjectManager
        projs = ProjectManager.list_projects()
        if len(projs) <= 1:
            return
        menu = ctk.CTkToplevel(self)
        menu.title("")
        menu.geometry(f"+{self.winfo_x() + 20}+{self.winfo_y() + self.winfo_height() - 200}")
        menu.overrideredirect(True)
        menu.grab_set()
        menu.lift()
        for name in projs:
            active = self._current_project and self._current_project.settings.name == name
            ctk.CTkButton(
                menu, text=name,
                font=ctk.CTkFont(size=12),
                fg_color=C["primary_container"] if active else "transparent",
                text_color=C["on_surface"],
                hover_color=C["surface_variant"],
                anchor="w", corner_radius=0,
                width=180, height=28,
                command=lambda n=name: (menu.destroy(), self.open_project(n)),
            ).pack(fill="x")
        # Click outside to close
        menu.bind("<FocusOut>", lambda e: menu.destroy())

    def _toggle_fold(self) -> None:
        if not self._fold_container or not self._fold_btn:
            return
        self._fold_open = not self._fold_open
        for child in self._fold_container.winfo_children():
            if self._fold_open:
                child.pack(fill="x", pady=1)
            else:
                child.pack_forget()
        self._fold_btn.configure(image=self._make_fold_icon())

    def _make_fold_icon(self):
        """Return chevron-up (open) or chevron-down (closed) icon."""
        name = "chevron-up" if self._fold_open else "chevron-down"
        return load_icon(name, size=14, color=C["outline"])

    def _add_nav_button(self, item: NavItem, parent=None) -> None:
        parent = parent or self._sidebar
        icon = load_icon(item.icon, size=18, color=C["on_surface_variant"])
        btn = ctk.CTkButton(
            parent,
            text=item.label,
            image=icon,
            font=ctk.CTkFont(size=13),
            compound="left",
            fg_color="transparent", text_color=C["on_surface_variant"],
            hover_color=C["surface_variant"], anchor="w",
            corner_radius=10, height=30,
            command=lambda pn=item.page_name: self._nav_to(pn),
        )
        btn.pack(fill="x", padx=0, pady=1)
        self._sidebar_buttons[item.page_name] = btn

    def _nav_to(self, page_name: str) -> None:
        handler = getattr(self, page_name, None)
        if handler:
            handler()

    def _update_nav(self, active: str = "") -> None:
        for name, btn in self._sidebar_buttons.items():
            is_active = name == active
            if is_active:
                icon = load_icon(
                    self._icon_name_for_page(name), size=18, color=C["primary"]
                )
                btn.configure(
                    fg_color=C["primary_container"],
                    text_color=C["primary"],
                    image=icon,
                )
            else:
                icon = load_icon(
                    self._icon_name_for_page(name), size=18, color=C["on_surface_variant"]
                )
                btn.configure(
                    fg_color="transparent",
                    text_color=C["on_surface_variant"],
                    image=icon,
                )

    def _icon_name_for_page(self, page_name: str) -> str:
        """Map page_name back to Lucide icon name."""
        mapping = {
            "show_dashboard": "layout-dashboard",
            "show_sql": "database",
            "show_wireguard": "lock",
            "show_firewall": "shield",
            "show_backup": "hard-drive",
            "show_system_info": "activity",
            "show_projects": "folder-open",
            "show_customers": "users",
            "show_settings": "settings",
        }
        return mapping.get(page_name, "layout-dashboard")

    # ═══════════════════════════════════════════════════════════════
    #  Page switching
    # ═══════════════════════════════════════════════════════════════

    def _switch_to(self, page_class: Type[ctk.CTkFrame], *args, **kwargs) -> None:
        """Clear content and show a new page with 60ms breathing room."""
        # Check workspace compatibility
        ws = getattr(page_class, "WORKSPACE", WorkspaceMode.BOTH)
        if ws not in (WorkspaceMode.BOTH, self._workspace):
            messagebox.showwarning(
                "不可用",
                f"该页面在 {self._workspace.value.title()} Mode 下不可用",
            )
            return

        for w in self._content.winfo_children():
            w.destroy()
        self.after(60, lambda: self._do_render(page_class, args, kwargs))

    def _do_render(self, page_class, args, kwargs) -> None:
        page = page_class(self._content, *args, **kwargs)
        page.pack(fill="both", expand=True)

    def set_status(self, text: str) -> None:
        self._sidebar_status.configure(text=text)

    def show_toast(self, message: str, type: str = "success", duration: int = 3000) -> None:
        """Show a floating toast notification."""
        ToastFrame(self._content, message, type, duration)

    def show_modal(self, title: str = "确认操作", message: str = "确定要执行此操作吗？",
                   confirm_text: str = "确认", cancel_text: str = "取消",
                   on_confirm: Optional[Callable] = None, danger: bool = True) -> None:
        """Show a themed confirmation modal (replaces messagebox)."""
        ModalConfirm(self, title, message, confirm_text, cancel_text, on_confirm, danger)

    def _nav_to_home(self) -> None:
        self.show_dashboard()

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
            self._switch_to(ClientDashboardPage, self, self._current_project)

    def show_sql(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_sql"
        self._update_nav("show_sql")
        self._switch_to(SQLPage, self, self._server_project)

    def show_wireguard(self) -> None:
        self._current_page = "show_wireguard"
        self._update_nav("show_wireguard")
        if self._workspace == WorkspaceMode.SERVER:
            self._switch_to(WireGuardServerPage, self, self._server_project)
        else:
            self._switch_to(WireGuardClientPage, self)

    def show_firewall(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_firewall"
        self._update_nav("show_firewall")
        self._switch_to(FirewallPage, self, self._server_project)

    def show_backup(self) -> None:
        if self._workspace != WorkspaceMode.SERVER:
            return
        self._current_page = "show_backup"
        self._update_nav("show_backup")
        self._switch_to(BackupCenterPage, self, self._server_project)

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
        self._current_page = "show_projects"
        self._update_nav("show_projects")
        self._switch_to(ProjectsPage, self)

    def show_customers(self) -> None:
        if self._workspace != WorkspaceMode.CLIENT:
            return
        self._current_page = "show_customers"
        self._update_nav("show_customers")
        self._switch_to(CustomersPage, self)

    # ═══════════════════════════════════════════════════════════════
    #  Shared pages
    # ═══════════════════════════════════════════════════════════════

    def show_settings(self) -> None:
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
            self._build_sidebar()
            self.show_dashboard()
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开项目: {exc}")

    def show_new_project(self) -> None:
        dlg = _NewProjectDialog(self)
        self.wait_window(dlg)
        result = dlg.result()
        if result is None:
            return

        name, ip, port, vpn_ip, subnet, remote_type, remote_id, remote_pass = result
        self._sidebar_status.configure(text="Creating project…")

        def _create() -> None:
            try:
                project = ProjectManager.create(
                    name=name, public_ip=ip, listen_port=port,
                    vpn_ip=vpn_ip, subnet=subnet,
                    remote_type=remote_type, remote_id=remote_id,
                    remote_password=remote_pass,
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
        self.geometry("440x560")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=C["card_bg"])

        ctk.CTkLabel(self, text="新建服务器项目",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(pady=(16, 12))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=0,
                                         fg_color=C["card_bg"])
        scroll.pack(fill="both", expand=True, padx=20)

        self._entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}

        for label, key, default, options in [
            ("项目名称", "name", "", None),
            ("公网 IP", "ip", "", None),
            ("远程类型", "remote_type", "帮我吧", ["帮我吧", "向日葵", "ToDesk", "RustDesk", "Other"]),
            ("远程号码", "remote_id", "", None),
            ("远程密码", "remote_pass", "", None),
            ("Listen Port", "port", "51820", None),
            ("Server VPN IP", "vpn_ip", "10.66.66.1", None),
            ("Subnet", "subnet", "10.66.66.0/24", None),
        ]:
            ctk.CTkLabel(scroll, text=label,
                         font=ctk.CTkFont(size=12),
                         text_color=C["on_surface_variant"],
                         anchor="w").pack(fill="x", pady=(8, 2))
            if options:
                var = ctk.StringVar(value=default)
                w = ctk.CTkOptionMenu(scroll, values=options,
                                       variable=var, font=ctk.CTkFont(size=12),
                                       fg_color=C["surface_variant"],
                                       text_color=C["on_surface"],
                                       button_color=C["outline_variant"],
                                       button_hover_color=C["primary_container"],
                                       dropdown_fg_color=C["card_bg"],
                                       dropdown_text_color=C["on_surface"],
                                       dropdown_hover_color=C["surface_variant"],
                                       corner_radius=6)
            else:
                w = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=12),
                                 fg_color=C["surface_variant"],
                                 text_color=C["on_surface"],
                                 corner_radius=6)
                if default:
                    w.insert(0, default)
            w.pack(fill="x", pady=(0, 2))
            self._entries[key] = w

        # Mask remote password
        if "remote_pass" in self._entries:
            self._entries["remote_pass"].configure(show="•")

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(pady=(20, 12))
        ctk.CTkButton(btn_frame, text="取消", width=100,
                       command=self.destroy,
                       font=ctk.CTkFont(size=13),
                       fg_color="transparent",
                       text_color=C["on_surface_variant"],
                       hover_color=C["surface_variant"],
                       corner_radius=8,
                       ).pack(side="left", padx=(0, 12))
        self._create_btn = ctk.CTkButton(
            btn_frame, text="创建", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["primary"],
            text_color=C["on_primary"],
            hover_color=C["primary_hover"],
            corner_radius=8,
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
            self._entries["remote_pass"].get().strip(),
        )
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None
