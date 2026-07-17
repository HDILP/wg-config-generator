"""Customers page — client management with remote info and optional WireGuard."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.theme import C, PAD
from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.project import Project
from utils.icon_loader import load_icon
from widgets.empty_state import EmptyState

if TYPE_CHECKING:
    from app.app import GPServerManager


class CustomersPage(ctk.CTkFrame):
    """View/manage clients. Focus: customer record (remote info), WG optional."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="客户管理",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        proj = ProjectManager.list_projects()
        if not proj:
            EmptyState(
                self, icon="users",
                text="还没有项目",
                subtext="请先在项目列表创建项目",
                button_text="去新建项目",
                on_click=self._app.show_new_project,
            ).pack(fill="both", expand=True)
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12,
                                                 fg_color=C["card_bg"])
        scroll.pack(fill="both", expand=True, padx=PAD["xl"], pady=(0, PAD["md"]))

        for pname in reversed(proj):
            try:
                project = ProjectManager.load(pname)
            except Exception:
                continue

            folder_icon = load_icon("folder-open", size=14, color=C["primary"])
            row_hdr = ctk.CTkFrame(scroll, fg_color="transparent")
            row_hdr.pack(fill="x", pady=(PAD["md"], PAD["sm"]))
            ctk.CTkLabel(row_hdr, text="", image=folder_icon).pack(side="left", padx=(0, PAD["sm"]))
            ctk.CTkLabel(
                row_hdr, text=pname,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=C["primary"],
            ).pack(side="left")

            if not project.clients:
                ctk.CTkLabel(
                    scroll, text="  暂无客户端",
                    font=ctk.CTkFont(size=12),
                    text_color=C["outline"],
                ).pack(anchor="w", padx=PAD["lg"])
            else:
                for c in project.clients:
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", padx=PAD["lg"], pady=2)

                    user_icon = load_icon("users", size=14, color=C["on_surface_variant"])
                    ctk.CTkLabel(row, text="", image=user_icon).pack(side="left", padx=(0, PAD["sm"]))
                    ctk.CTkLabel(
                        row, text=c.name,
                        font=ctk.CTkFont(size=13),
                        text_color=C["on_surface"],
                        width=120, anchor="w",
                    ).pack(side="left")

                    rid_lbl = ctk.CTkLabel(
                        row, text=c.remote_id or "—",
                        font=ctk.CTkFont(size=11),
                        text_color=C["outline"], width=120,
                    )
                    rid_lbl.pack(side="left")

                    if c.remote_id:
                        copy_icon = load_icon("file-text", size=12, color=C["outline"])
                        ctk.CTkButton(
                            row, text="", image=copy_icon, width=22, height=22,
                            font=ctk.CTkFont(size=9),
                            fg_color="transparent", text_color=C["outline"],
                            hover_color=C["surface_variant"], corner_radius=4,
                            command=lambda v=c.remote_id: self._copy(v),
                        ).pack(side="left", padx=1)

                    if c.remote_password:
                        lock_icon = load_icon("lock", size=12, color=C["outline"])
                        ctk.CTkButton(
                            row, text="", image=lock_icon, width=22, height=22,
                            font=ctk.CTkFont(size=9),
                            fg_color="transparent", text_color=C["outline"],
                            hover_color=C["surface_variant"], corner_radius=4,
                            command=lambda v=c.remote_password: self._copy(v),
                        ).pack(side="left", padx=1)

                    # Edit button
                    edit_icon = load_icon("file-text", size=12, color=C["primary"])
                    ctk.CTkButton(
                        row, text="", image=edit_icon, width=22, height=22,
                        font=ctk.CTkFont(size=9),
                        fg_color="transparent", text_color=C["primary"],
                        hover_color=C["primary_container"], corner_radius=4,
                        command=lambda pname=pname, c=c: self._edit_client(pname, c),
                    ).pack(side="left", padx=1)

        ctk.CTkButton(
            self, text="＋ 新建客户",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["primary"],
            text_color=C["on_primary"],
            hover_color=C["primary_hover"],
            corner_radius=8,
            command=self._add_customer,
        ).pack(anchor="w", padx=PAD["xl"], pady=(0, PAD["md"]))

    def _copy(self, val: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(val)

    def _add_customer(self) -> None:
        p = self._app.get_current_project()
        if not p:
            pnames = ProjectManager.list_projects()
            if not pnames:
                messagebox.showwarning("提示", "请先创建项目")
                return
            p = ProjectManager.load(pnames[-1])

        dlg = _CustomerDialog(self, p)
        self.wait_window(dlg)
        res = dlg.result()
        if res is None:
            return
        orig_name, name, remote_id, remote_pass, create_wg, is_edit = res
        if is_edit:
            threading.Thread(target=self._edit_worker,
                             args=(p.name, orig_name, name, remote_id, remote_pass),
                             daemon=True).start()
        else:
            threading.Thread(target=self._add_worker,
                             args=(p.name, name, remote_id, remote_pass, create_wg),
                             daemon=True).start()

    def _edit_client(self, pname: str, client) -> None:
        p = ProjectManager.load(pname)
        dlg = _CustomerDialog(self, p, client=client)
        self.wait_window(dlg)
        res = dlg.result()
        if res is None:
            return
        orig_name, name, remote_id, remote_pass, _, _ = res
        threading.Thread(target=self._edit_worker,
                         args=(pname, orig_name, name, remote_id, remote_pass),
                         daemon=True).start()

    def _edit_worker(self, pname, orig_name, name, remote_id, remote_pass):
        try:
            p = ProjectManager.load(pname)
            for c in p.clients:
                if c.name == orig_name:
                    c.name = name
                    c.remote_id = remote_id
                    c.remote_password = remote_pass
                    break
            ProjectManager.save(p)
            self.after(0, self._build)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("错误", str(exc)))

    def _add_worker(self, pname, name, remote_id, remote_pass, create_wg):
        try:
            p = ProjectManager.load(pname)
            if create_wg:
                ProjectManager.add_client(p, name)
                p = ProjectManager.load(pname)
                for c in p.clients:
                    if c.name == name:
                        c.remote_type = "帮我吧"
                        c.remote_id = remote_id
                        c.remote_password = remote_pass
                        break
                ProjectManager.save(p)
            else:
                o = p.settings.ops
                if remote_id:
                    o.remote_id = remote_id
                if remote_pass:
                    o.password = remote_pass
                ProjectManager.save(p)
            self.after(0, self._build)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("错误", str(exc)))


class _CustomerDialog(ctk.CTkToplevel):
    """Dialog: name + remote info. Edit mode if client is provided."""

    def __init__(self, parent, project: Project, client=None):
        super().__init__(parent)
        is_edit = client is not None
        self._edit_name = client.name if is_edit else ""
        self.title(f"{'编辑' if is_edit else '新建'}客户 — {project.name}")
        self.geometry("400x320")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="客户名称", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(16, 4))
        self._name = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._name.insert(0, client.name if is_edit else "")
        self._name.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(self, text="远程号码", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(4, 4))
        self._rid = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._rid.insert(0, client.remote_id or "" if is_edit else "")
        self._rid.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(self, text="远程密码", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(4, 4))
        self._rpwd = ctk.CTkEntry(self, font=ctk.CTkFont(size=13), show="•")
        self._rpwd.insert(0, client.remote_password or "" if is_edit else "")
        self._rpwd.pack(fill="x", padx=20, pady=(0, 4))

        if not is_edit:
            self._wg_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(self, text="同时创建 WireGuard 客户端",
                            variable=self._wg_var,
                            font=ctk.CTkFont(size=13),
                            ).pack(anchor="w", padx=20, pady=(8, 4))
            ctk.CTkLabel(self, text="不勾选则仅保存远程信息到项目",
                         font=ctk.CTkFont(size=10),
                         text_color=C["outline"],
                         ).pack(anchor="w", padx=24)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(12, 12))
        ctk.CTkButton(btn_frame, text="取消", width=80,
                       command=self.destroy,
                       font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="保存" if is_edit else "创建",
                       command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       ).pack(side="right")

        self._confirmed = False
        self._is_edit = is_edit
        self._name.focus_set()

    def _confirm(self) -> None:
        if not self._name.get().strip():
            messagebox.showwarning("验证", "客户名称不能为空", parent=self)
            return
        self._confirmed = True
        self._result = (
            self._edit_name,       # original name for lookup
            self._name.get().strip(),
            self._rid.get().strip(),
            self._rpwd.get().strip(),
            self._wg_var.get() if not self._is_edit else False,
            self._is_edit,
        )
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None
