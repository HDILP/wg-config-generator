"""Client Dashboard — project overview with inline Ops info for Client Mode."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.project import Project
from utils.icon_loader import load_icon
from widgets import CardFrame

if TYPE_CHECKING:
    from app.app import GPServerManager


class ClientDashboardPage(ctk.CTkFrame):
    """Client mode dashboard: project stats + inline ops editor."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager,
                 project: Optional[Project] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._ops_entries: Dict[str, ctk.CTkEntry | ctk.CTkOptionMenu] = {}
        self._ops_card: Optional[CardFrame] = None
        self._status_lbl: Optional[ctk.CTkLabel] = None
        self._build()

    def _build(self) -> None:
        p = self._project

        if p:
            self._build_project_view(p)
        else:
            self._build_overview()

    # ── Project view ──────────────────────────────────────────────

    def _build_project_view(self, p: Project) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        ctk.CTkLabel(
            header, text=p.settings.name,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=f"{p.settings.public_ip or '未设置IP'}  |  {len(p.clients)} 个客户端",
            font=ctk.CTkFont(size=12),
            text_color=C["outline"],
        ).pack(side="right")

        # Two-column layout: left = server info, right = ops info
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=PAD["xl"])
        cols.grid_columnconfigure(0, weight=1)
        cols.grid_columnconfigure(1, weight=1)

        # Left: Server info card
        info_card = CardFrame(cols, title="服务器信息")
        info_card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD["md"]))

        for label, val in [
            ("VPN 地址", p.settings.vpn_ip),
            ("子网", p.settings.subnet),
            ("监听端口", str(p.settings.listen_port)),
            ("远程方式", p.settings.ops.remote_type or p.settings.remote.type or "未设置"),
        ]:
            row = ctk.CTkFrame(info_card, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=3)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         text_color=C["outline"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         text_color=C["on_surface"],
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Right: Ops info inline editor
        self._ops_card = CardFrame(cols, title="运维信息")
        self._ops_card.grid(row=0, column=1, sticky="nsew", padx=(PAD["md"], 0))

        o = p.settings.ops
        fields = [
            ("远程软件", "remote_type", o.remote_type,
             ["帮我吧", "向日葵", "ToDesk", "RustDesk", "Other"]),
            ("远程号码", "remote_id", o.remote_id, None),
            ("负责人", "contact", o.contact, None),
            ("密码", "password", o.password, None),
            ("备注", "note", o.note, None),
            ("服务器地区", "region", o.region, None),
            ("SQL 版本", "sql_version", o.sql_version, None),
            ("管家婆版本", "gp_version", o.gp_version, None),
        ]

        for label, key, default, options in fields:
            row = ctk.CTkFrame(self._ops_card, fg_color="transparent")
            row.pack(fill="x", padx=PAD["lg"], pady=2)

            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11),
                         text_color=C["outline"],
                         width=70, anchor="w").pack(side="left")

            if options:
                var = ctk.StringVar(value=default or options[0])
                w = ctk.CTkOptionMenu(
                    row, values=options, variable=var,
                    font=ctk.CTkFont(size=11),
                    fg_color=C["surface_variant"],
                    text_color=C["on_surface"],
                    button_color=C["outline_variant"],
                    button_hover_color=C["primary_container"],
                    dropdown_fg_color=C["card_bg"],
                    dropdown_text_color=C["on_surface"],
                    dropdown_hover_color=C["surface_variant"],
                    corner_radius=6,
                    height=24,
                )
            else:
                w = ctk.CTkEntry(
                    row, font=ctk.CTkFont(size=11),
                    fg_color=C["surface_variant"],
                    text_color=C["on_surface"],
                    corner_radius=6, height=24,
                )
                w.insert(0, default or "")
                if key == "password":
                    w.configure(show="•")

            w.pack(side="left", fill="x", expand=True, padx=(PAD["sm"], 0))

            # Copy button for remote_id and password
            if key in ("remote_id", "password"):
                copy_icon = load_icon("file-text", size=12, color=C["outline"])
                ctk.CTkButton(
                    row, text="", image=copy_icon, width=22, height=22,
                    font=ctk.CTkFont(size=9),
                    fg_color="transparent", text_color=C["outline"],
                    hover_color=C["surface_variant"], corner_radius=4,
                    command=lambda k=key: self._copy_field(k),
                ).pack(side="left", padx=(PAD["sm"], 0))

            self._ops_entries[key] = w

        # Save button
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD["xl"], pady=PAD["md"])

        ctk.CTkButton(
            btn_row, text="💾 保存运维信息",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["primary"],
            text_color=C["on_primary"],
            hover_color=C["primary_hover"],
            corner_radius=8,
            command=self._save_ops,
        ).pack(side="right")

        self._status_lbl = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=11),
            text_color=C["outline"],
        )
        self._status_lbl.pack(side="left")

    def _copy_field(self, key: str) -> None:
        val = ""
        w = self._ops_entries.get(key)
        if isinstance(w, ctk.CTkEntry):
            val = w.get()
        self.clipboard_clear()
        self.clipboard_append(val)
        if self._status_lbl:
            self._status_lbl.configure(text=f"✓ 已复制 {key}")
            self.after(2000, lambda: self._status_lbl.configure(text=""))

    def _save_ops(self) -> None:
        if not self._project:
            return
        o = self._project.settings.ops
        o.remote_type = self._ops_entries["remote_type"].get()
        o.remote_id = self._ops_entries["remote_id"].get()
        o.contact = self._ops_entries["contact"].get()
        o.password = self._ops_entries["password"].get()
        o.note = self._ops_entries["note"].get()
        o.region = self._ops_entries["region"].get()
        o.sql_version = self._ops_entries["sql_version"].get()
        o.gp_version = self._ops_entries["gp_version"].get()

        # Sync remote info to project-level remote
        self._project.settings.remote.type = o.remote_type
        self._project.settings.remote.id = o.remote_id

        ProjectManager.save(self._project)
        if self._status_lbl:
            self._status_lbl.configure(text="✓ 运维信息已保存")
            self.after(2000, lambda: self._status_lbl.configure(text=""))

    # ── Overview (no project) ─────────────────────────────────────

    def _build_overview(self) -> None:
        ctk.CTkLabel(
            self, text="Client Dashboard",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        proj = ProjectManager.list_projects()
        total_clients = sum(
            len(ProjectManager.load(n).clients) for n in proj[-50:]
        )

        # Stat pills
        pills_frame = ctk.CTkFrame(self, fg_color=C["container_bg"], corner_radius=CR)
        pills_frame.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))

        for i, (icon_name, label, val) in enumerate([
            ("folder-open", "项目", len(proj)),
            ("users", "客户端", total_clients),
        ]):
            pill = ctk.CTkFrame(pills_frame, fg_color=C["card_bg"], corner_radius=CR, border_width=1, border_color=C["outline_variant"])
            pill.grid(row=0, column=i, sticky="nsew", padx=4, pady=PAD["md"])
            pills_frame.grid_columnconfigure(i, weight=1)

            icon = load_icon(icon_name, size=20, color=C["primary"])
            ctk.CTkLabel(pill, text="", image=icon).pack(pady=(PAD["lg"], 0))
            ctk.CTkLabel(
                pill, text=str(val),
                font=ctk.CTkFont(size=26, weight="bold"),
                text_color=C["primary"],
            ).pack()
            ctk.CTkLabel(
                pill, text=label,
                font=ctk.CTkFont(size=11),
                text_color=C["outline"],
            ).pack(pady=(0, PAD["lg"]))

        # Recent projects
        recent_card = CardFrame(self, title="最近项目")
        recent_card.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))

        if not proj:
            from widgets.empty_state import EmptyState
            EmptyState(
                recent_card,
                icon="folder-open",
                text="还没有项目",
                subtext="请在项目列表新建第一个项目",
                button_text="新建项目",
                on_click=self._app.show_new_project,
            ).pack(fill="both", expand=True)
        else:
            for name in reversed(proj[-8:]):
                folder_icon = load_icon("folder-open", size=14, color=C["on_surface_variant"])
                row = ctk.CTkButton(
                    recent_card, text=f"  {name}",
                    image=folder_icon,
                    font=ctk.CTkFont(size=13),
                    compound="left",
                    fg_color="transparent",
                    text_color=C["on_surface"],
                    hover_color=C["surface_variant"],
                    anchor="w", corner_radius=6, height=30,
                    command=lambda n=name: self._app.open_project(n),
                )
                row.pack(fill="x", padx=PAD["sm"], pady=1)

            ctk.CTkButton(
                self, text="➕ 新建项目",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=C["primary"],
                text_color=C["on_primary"],
                hover_color=C["primary_hover"],
                corner_radius=8,
                command=self._app.show_new_project,
            ).pack(anchor="w", padx=PAD["xl"])
