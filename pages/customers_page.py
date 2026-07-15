"""Customers page — client management with remote info and optional WireGuard."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.project import Project
from widgets import Card, PrimaryButton

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
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 8))

        proj = ProjectManager.list_projects()
        if not proj:
            ctk.CTkLabel(self, text="暂无项目",
                         font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=20)
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        for pname in reversed(proj):
            try:
                project = ProjectManager.load(pname)
            except Exception:
                continue

            ctk.CTkLabel(scroll, text=f"📁  {pname}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#6750A4",
                         ).pack(anchor="w", pady=(12, 4))

            if not project.clients:
                ctk.CTkLabel(scroll, text="  暂无客户端",
                             font=ctk.CTkFont(size=12),
                             text_color="#79747E",
                             ).pack(anchor="w", padx="16")
            else:
                for c in project.clients:
                    row = Card(scroll, corner_radius=8)
                    row.pack(fill="x", padx=16, pady=2)

                    ctk.CTkLabel(row, text=f"👤  {c.name}",
                                 font=ctk.CTkFont(size=13),
                                 width=120, anchor="w").pack(side="left")

                    rid_lbl = ctk.CTkLabel(row, text=c.remote_id or "—",
                                           font=ctk.CTkFont(size=11),
                                           text_color="#79747E", width=120)
                    rid_lbl.pack(side="left")

                    if c.remote_id:
                        ctk.CTkButton(row, text="📋", width=24, height=22,
                                      font=ctk.CTkFont(size=9),
                                      command=lambda v=c.remote_id: self._copy(v),
                                      ).pack(side="left", padx=1)

                    if c.remote_password:
                        ctk.CTkButton(row, text="🔑", width=24, height=22,
                                      font=ctk.CTkFont(size=9),
                                      command=lambda v=c.remote_password: self._copy(v),
                                      ).pack(side="left", padx=1)

        PrimaryButton(self, text="＋ 新建客户",
                       font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color="#2b7a4b",
                       command=self._add_customer,
                       ).pack(anchor="w", padx=24)

    def _copy(self, val: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(val)
        self._set_status(f"✓ 已复制")

    def _set_status(self, text: str) -> None:
        pass

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
        name, remote_id, remote_pass, create_wg = res
        self._set_status("Adding…")
        threading.Thread(target=self._add_worker,
                         args=(p.name, name, remote_id, remote_pass, create_wg),
                         daemon=True).start()

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
    """Dialog: name + remote info + optional WireGuard client creation."""

    def __init__(self, parent, project: Project):
        super().__init__(parent)
        self.title(f"新建客户 — {project.name}")
        self.geometry("400x320")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="客户名称", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(16, 4))
        self._name = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._name.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(self, text="远程号码", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(4, 4))
        self._rid = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._rid.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(self, text="远程密码", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(4, 4))
        self._rpwd = ctk.CTkEntry(self, font=ctk.CTkFont(size=13), show="•")
        self._rpwd.pack(fill="x", padx=20, pady=(0, 4))

        self._wg_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self, text="同时创建 WireGuard 客户端",
                        variable=self._wg_var,
                        font=ctk.CTkFont(size=13),
                        ).pack(anchor="w", padx=20, pady=(8, 4))

        ctk.CTkLabel(self, text="不勾选则仅保存远程信息到项目",
                     font=ctk.CTkFont(size=10),
                     text_color="#79747E",
                     ).pack(anchor="w", padx=24)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(12, 12))
        ctk.CTkButton(btn_frame, text="取消", width=80,
                       command=self.destroy,
                       font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        PrimaryButton(btn_frame, text="创建", command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       ).pack(side="right")

        self._confirmed = False
        self._name.focus_set()

    def _confirm(self) -> None:
        if not self._name.get().strip():
            messagebox.showwarning("验证", "客户名称不能为空", parent=self)
            return
        self._confirmed = True
        self._result = (
            self._name.get().strip(),
            self._rid.get().strip(),
            self._rpwd.get().strip(),
            self._wg_var.get(),
        )
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None
