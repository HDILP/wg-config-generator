"""System Info page — server diagnostics for Server Mode."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from services.system_service import get_system_info, ping, public_ip, restart_service

if TYPE_CHECKING:
    from app.app import GPServerManager


class SystemInfoPage(ctk.CTkFrame):
    """System information and service management (Server Mode)."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, tab: str = "system", **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._tab = tab
        self._build()

    def _build(self) -> None:
        title = "系统信息" if self._tab == "system" else "服务管理"
        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        # Sub-tabs
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=24, pady=(0, 12))

        self._tab_var = ctk.StringVar(value=self._tab)
        for label, val in [("系统信息", "system"), ("服务管理", "services")]:
            ctk.CTkRadioButton(tab_frame, text=label, variable=self._tab_var,
                               value=val, font=ctk.CTkFont(size=13),
                               command=self._switch_tab,
                               ).pack(side="left", padx=(0, 16))

        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._content_frame.pack(fill="both", expand=True, padx=24)

        self._switch_tab()

    def _switch_tab(self) -> None:
        for w in self._content_frame.winfo_children():
            w.destroy()

        if self._tab_var.get() == "system":
            self._build_system()
        else:
            self._build_services()

    # ═══════════════════════════════════════════════════════════════
    #  System Info tab
    # ═══════════════════════════════════════════════════════════════

    def _build_system(self) -> None:
        container = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # Info cards
        card = ctk.CTkFrame(container, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        self._sys_labels = {}
        for label in ["CPU 使用率", "内存使用率", "磁盘使用率", "公网 IP"]:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13),
                         width=100, anchor="w").pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=13),
                               anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self._sys_labels[label] = val

        # Tools
        tool_card = ctk.CTkFrame(container, corner_radius=12)
        tool_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(tool_card, text="诊断工具",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        tools_frame = ctk.CTkFrame(tool_card, fg_color="transparent")
        tools_frame.pack(fill="x", padx=16, pady=(0, 10))

        for text, cmd in [
            ("Ping 8.8.8.8", lambda: self._run("ping", "8.8.8.8")),
            ("检测公网 IP", self._detect_ip),
        ]:
            ctk.CTkButton(tools_frame, text=text, width=130, height=30,
                           font=ctk.CTkFont(size=12),
                           command=cmd).pack(side="left", padx=(0, 8))

        # Output
        ctk.CTkLabel(container, text="输出",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     ).pack(anchor="w", pady=(8, 4))
        self._output = ctk.CTkTextbox(container, height=100, corner_radius=8,
                                       font=ctk.CTkFont(size=11, family="Consolas"))
        self._output.pack(fill="x", pady=(0, 8))

        self._status = ctk.CTkLabel(container, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack()

        # Auto-load
        self._load_system_info()

    def _load_system_info(self) -> None:
        threading.Thread(target=self._sys_info_worker, daemon=True).start()

    def _sys_info_worker(self) -> None:
        try:
            info = get_system_info()
            self.after(0, lambda: self._sys_labels["CPU 使用率"].configure(
                text=f"{info.cpu_percent}%"))
            self.after(0, lambda: self._sys_labels["内存使用率"].configure(
                text=f"{info.memory_percent}%"))
            self.after(0, lambda: self._sys_labels["磁盘使用率"].configure(
                text=f"{info.disk_percent}%"))
        except Exception:
            pass
        try:
            ext_ip = public_ip()
            self.after(0, lambda: self._sys_labels["公网 IP"].configure(text=ext_ip))
        except Exception:
            pass

    def _run(self, tool: str, target: str) -> None:
        self._output.insert("end", f"Running {tool} {target}…\n")
        self._output.see("end")

    def _detect_ip(self) -> None:
        self._output.insert("end", "Detecting public IP…\n")
        def _work():
            try:
                ip = public_ip()
                self.after(0, lambda: (
                    self._output.insert("end", f"Public IP: {ip}\n"),
                    self._output.see("end"),
                ))
            except Exception as exc:
                self.after(0, lambda: (
                    self._output.insert("end", f"Error: {exc}\n"),
                    self._output.see("end"),
                ))
        threading.Thread(target=_work, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    #  Services tab
    # ═══════════════════════════════════════════════════════════════

    def _build_services(self) -> None:
        container = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)

        card = ctk.CTkFrame(container, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(card, text="Windows 服务管理",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(row, text="服务名称", font=ctk.CTkFont(size=13),
                     width=80).pack(side="left")
        self._svc_entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=13))
        self._svc_entry.insert(0, "MSSQL$MSSQLSERVER")
        self._svc_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkButton(row, text="重启", width=60, height=28,
                       font=ctk.CTkFont(size=11), fg_color="#FF9800",
                       command=self._restart_svc,
                       ).pack(side="left", padx=(8, 0))

        # Common services
        ctk.CTkLabel(card, text="常用服务",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#79747E",
                     ).pack(anchor="w", padx=16, pady=(8, 4))

        for svc_name, svc_label in [
            ("MSSQL$MSSQLSERVER", "SQL Server"),
            ("WireGuardTunnel$*", "WireGuard"),
            ("MSSQLFDLauncher", "SQL 全文搜索"),
        ]:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=svc_label, font=ctk.CTkFont(size=13),
                         width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=svc_name, font=ctk.CTkFont(size=11),
                         text_color="#79747E",
                         anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="重启", width=50, height=24,
                           font=ctk.CTkFont(size=10), fg_color="#FF9800",
                           command=lambda n=svc_name: self._restart_named(n),
                           ).pack(side="right")

        self._svc_output = ctk.CTkLabel(container, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color="#79747E")
        self._svc_output.pack(pady=8)

    def _restart_svc(self) -> None:
        name = self._svc_entry.get().strip()
        if not name:
            return
        self._svc_output.configure(text=f"Restarting {name}…")
        threading.Thread(target=lambda: self.after(0, lambda: self._svc_output.configure(
            text=restart_service(name)),
        ), daemon=True).start()

    def _restart_named(self, name: str) -> None:
        self._svc_output.configure(text=f"Restarting {name}…")
        threading.Thread(target=lambda: self.after(0, lambda: self._svc_output.configure(
            text=restart_service(name)),
        ), daemon=True).start()
