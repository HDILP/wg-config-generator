"""WireGuard page — server info, client list, add/remove/export/regen."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from core.project_manager import ProjectManager
from models.project import Project
from utils.file_ops import open_folder

if TYPE_CHECKING:
    from app.app import GPServerManager


class WireGuardPage(ctk.CTkFrame):
    """WireGuard management: server info + client CRUD."""

    def __init__(self, master, app: GPServerManager, project: Project, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._build()

    def refresh(self) -> None:
        # Reload project from disk
        self._project = ProjectManager.load(self._project.name)
        self._clear()
        self._build()

    def _clear(self) -> None:
        for w in self.winfo_children():
            w.destroy()

    def _build(self) -> None:
        p = self._project
        s = p.settings

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            hdr, text="WireGuard", font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            hdr, text="📁 打开目录", width=90, height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: open_folder(p.dir),
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            hdr, text="🔄 刷新", width=70, height=28,
            font=ctk.CTkFont(size=11),
            command=self.refresh,
        ).pack(side="right")

        # Server info
        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(info, text="服务器信息", font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        rows = [
            ("公网 IP", s.public_ip or "未设置"),
            ("VPN 地址", f"{s.vpn_ip}/24"),
            ("监听端口", str(s.listen_port)),
            ("公钥", p.server_keypair.public[:32] + "..." if p.server_keypair.public else "未生成"),
        ]
        for label, val in rows:
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         text_color="#79747E", width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Client list
        ctk.CTkLabel(self, text=f"客户端 ({len(p.clients)})",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(8, 6))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12, height=200)
        scroll.pack(fill="x", padx=24, pady=(0, 12))

        if not p.clients:
            ctk.CTkLabel(scroll, text="暂无客户端", text_color="#79747E",
                         font=ctk.CTkFont(size=12)).pack(pady=20)
        else:
            for i, c in enumerate(p.clients, 1):
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=8)

                ctk.CTkLabel(row, text=f"{i}.", font=ctk.CTkFont(size=12),
                             width=24).pack(side="left")
                ctk.CTkLabel(row, text=c.name, font=ctk.CTkFont(size=13),
                             anchor="w", width=120).pack(side="left")
                ctk.CTkLabel(row, text=c.vpn_ip, font=ctk.CTkFont(size=12),
                             text_color="#79747E", width=100).pack(side="left")
                status_icon = "●" if c.status.value == "active" else "○"
                status_color = "#4CAF50" if c.status.value == "active" else "#9E9E9E"
                ctk.CTkLabel(row, text=status_icon, font=ctk.CTkFont(size=12),
                             text_color=status_color, width=20).pack(side="left")

                # Actions
                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right")
                ctk.CTkButton(
                    btn_frame, text="📁", width=28, height=24,
                    font=ctk.CTkFont(size=10),
                    command=lambda n=c.name: open_folder(p.dir / "clients" / n),
                ).pack(side="left", padx=2)
                ctk.CTkButton(
                    btn_frame, text="🔄", width=28, height=24,
                    font=ctk.CTkFont(size=10),
                    command=lambda n=c.name: self._regen_client(n),
                ).pack(side="left", padx=2)
                ctk.CTkButton(
                    btn_frame, text="✕", width=28, height=24,
                    fg_color="#b33", hover_color="#922",
                    font=ctk.CTkFont(size=10),
                    command=lambda n=c.name: self._remove_client(n),
                ).pack(side="left", padx=2)

        # Actions
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", padx=24)

        ctk.CTkButton(
            act, text="← 返回仪表盘", width=110,
            font=ctk.CTkFont(size=12),
            command=lambda: self._app.show_dashboard(),
        ).pack(side="left")

        ctk.CTkButton(
            act, text="＋ 新增客户端",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b7a4b", hover_color="#1e5f38",
            command=self._add_client,
        ).pack(side="right")

        # Status
        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(8, 4))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _add_client(self) -> None:
        p = self._project
        base = ".".join(p.settings.vpn_ip.split(".")[:3])
        used = {c.vpn_ip for c in p.clients} | {p.settings.vpn_ip}
        suggest = "10.66.66.2"
        for i in range(2, 255):
            ip = f"{base}.{i}"
            if ip not in used:
                suggest = ip
                break

        dlg = _AddClientDialog(self, suggest)
        self.wait_window(dlg)
        res = dlg.result()
        if res is None:
            return
        name, ip = res

        self._set_status(f"Adding client {name}…")
        threading.Thread(target=self._add_worker, args=(name, ip or None),
                         daemon=True).start()

    def _add_worker(self, name: str, ip: Optional[str]) -> None:
        try:
            ProjectManager.add_client(self._project, name, ip)
            self.after(0, self.refresh)
            self.after(0, lambda: self._set_status(f"✓ {name} added"))
        except Exception as exc:
            self.after(0, lambda: (
                self._set_status(f"✗ {exc}"),
                messagebox.showerror("Error", str(exc)),
            ))

    def _remove_client(self, name: str) -> None:
        if not messagebox.askyesno("确认", f"确定删除客户端 '{name}'？"):
            return
        self._set_status(f"Removing {name}…")
        threading.Thread(target=self._remove_worker, args=(name,),
                         daemon=True).start()

    def _remove_worker(self, name: str) -> None:
        try:
            ProjectManager.remove_client(self._project, name)
            self.after(0, self.refresh)
            self.after(0, lambda: self._set_status(f"✓ {name} removed"))
        except Exception as exc:
            self.after(0, lambda: (
                self._set_status(f"✗ {exc}"),
                messagebox.showerror("Error", str(exc)),
            ))

    def _regen_client(self, name: str) -> None:
        if not messagebox.askyesno("确认", f"重新生成客户端 '{name}' 的密钥？"):
            return
        self._set_status(f"Regenerating {name}…")
        threading.Thread(target=self._regen_worker, args=(name,),
                         daemon=True).start()

    def _regen_worker(self, name: str) -> None:
        try:
            self._project = ProjectManager.regenerate_client(self._project, name)
            self.after(0, self.refresh)
            self.after(0, lambda: self._set_status(f"✓ {name} regenerated"))
        except Exception as exc:
            self.after(0, lambda: (
                self._set_status(f"✗ {exc}"),
                messagebox.showerror("Error", str(exc)),
            ))


class _AddClientDialog(ctk.CTkToplevel):
    """Small popup for client name + optional IP."""

    def __init__(self, parent, suggested_ip: str):
        super().__init__(parent)
        self.title("新增客户端")
        self.geometry("380x200")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="客户端名称", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(16, 4))
        self._name = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._name.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(self, text="VPN IP（留空自动分配）",
                     font=ctk.CTkFont(size=13), anchor="w",
                     ).pack(fill="x", padx=20, pady=(4, 4))
        self._ip = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._ip.insert(0, suggested_ip)
        self._ip.pack(fill="x", padx=20, pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        ctk.CTkButton(btn_frame, text="取消", command=self.destroy,
                       font=ctk.CTkFont(size=12), width=80,
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="添加", command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       ).pack(side="right")

        self._name.focus_set()
        self._confirmed = False
        self.grab_set()

    def _confirm(self) -> None:
        if not self._name.get().strip():
            messagebox.showwarning("验证", "客户端名称不能为空", parent=self)
            return
        self._confirmed = True
        self._result = (self._name.get().strip(), self._ip.get().strip())
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None
