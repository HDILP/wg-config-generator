"""CustomTkinter GUI — Project Manager for WireGuard."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from generator import ProjectManager
from keygen import check_wg_available
from models import Project
from utils import open_folder


class _AddClientDialog(ctk.CTkToplevel):
    """Small popup for client name + optional IP."""

    def __init__(self, parent: ctk.CTkBaseClass, suggested_ip: str) -> None:
        super().__init__(parent)
        self.title("New Client")
        self.geometry("380x200")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="Client Name", font=ctk.CTkFont(size=13),
                     anchor="w").pack(fill="x", padx=20, pady=(16, 4))
        self._name = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._name.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(self, text="VPN IP (leave blank for auto)",
                     font=ctk.CTkFont(size=13), anchor="w"
                     ).pack(fill="x", padx=20, pady=(4, 4))
        self._ip = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._ip.insert(0, suggested_ip)
        self._ip.pack(fill="x", padx=20, pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy,
                       font=ctk.CTkFont(size=12), width=80
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Add", command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       ).pack(side="right")

        self._name.focus_set()
        self._confirmed = False
        self.grab_set()

    def _confirm(self) -> None:
        if not self._name.get().strip():
            messagebox.showwarning("Validation", "Client name is required.",
                                   parent=self)
            return
        self._confirmed = True
        self._result = (self._name.get().strip(), self._ip.get().strip())
        self.destroy()

    def result(self) -> tuple[str, str] | None:
        return self._result if self._confirmed else None


class WireGuardGUI(ctk.CTk):
    """Main app — page-based UI for project management."""

    WIDTH, HEIGHT = 540, 640

    def __init__(self) -> None:
        super().__init__()
        self.title("WireGuard Project Manager")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._wg_error: Optional[str] = check_wg_available()
        if self._wg_error:
            self._build_error_ui()
            return

        self._container = ctk.CTkFrame(self, corner_radius=12)
        self._container.pack(expand=True, fill="both", padx=20, pady=20)
        self._current_project: Optional[Project] = None
        self._show_home()

    # ═══════════════════════════════════════════════════════════
    #  page helpers
    # ═══════════════════════════════════════════════════════════

    def _clear(self) -> None:
        for w in self._container.winfo_children():
            w.destroy()

    def _home(self) -> None:
        self._current_project = None
        self._show_home()

    # ═══════════════════════════════════════════════════════════
    #  error
    # ═══════════════════════════════════════════════════════════

    def _build_error_ui(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=30, pady=30)
        ctk.CTkLabel(
            frame, text="⚠️  WireGuard Not Found",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(30, 10))
        ctk.CTkLabel(
            frame, text=self._wg_error or "", wraplength=400,
            font=ctk.CTkFont(size=13), text_color="gray40",
        ).pack(pady=10)
        ctk.CTkLabel(
            frame,
            text="Install WireGuard and ensure `wg` is on PATH,\nthen restart.",
            wraplength=400, font=ctk.CTkFont(size=12), text_color="gray50",
        ).pack(pady=(5, 12))

        btn_kw = dict(height=40, corner_radius=8, font=ctk.CTkFont(size=14, weight="bold"))
        if os.path.exists(self._bundled_installer()):
            ctk.CTkButton(
                frame, text="⚡  一键安装 WireGuard",
                command=self._run_installer, **btn_kw,
            ).pack(fill="x", padx=40, pady=(0, 8))
        ctk.CTkButton(
            frame, text="重启本程序", command=lambda: os.execl(sys.executable, sys.executable, *sys.argv),
            fg_color="gray40", hover_color="gray30", **btn_kw,
        ).pack(fill="x", padx=40)

    # ═══════════════════════════════════════════════════════════
    #  HOME
    # ═══════════════════════════════════════════════════════════

    def _show_home(self) -> None:
        self._clear()
        ctk.CTkLabel(
            self._container, text="WireGuard Project Manager",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(30, 8))
        ctk.CTkLabel(
            self._container, text="管家婆代理商专用",
            font=ctk.CTkFont(size=13), text_color="gray50",
        ).pack(pady=(0, 32))

        btn_kw = dict(height=56, corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"))

        ctk.CTkButton(
            self._container, text="＋  新建服务器", fg_color="#2b7a4b",
            hover_color="#1e5f38",
            command=self._show_new_server, **btn_kw,
        ).pack(fill="x", padx=40, pady=(0, 12))

        ctk.CTkButton(
            self._container, text="📂  打开已有服务器", fg_color="#2a6d9c",
            hover_color="#1f5275",
            command=self._show_project_list, **btn_kw,
        ).pack(fill="x", padx=40, pady=(0, 32))

    # ═══════════════════════════════════════════════════════════
    #  NEW SERVER
    # ═══════════════════════════════════════════════════════════

    def _show_new_server(self) -> None:
        self._clear()
        ctk.CTkLabel(
            self._container, text="新建服务器",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(16, 12))

        fields_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        fields_frame.pack(fill="x", padx=20)

        entries: dict[str, ctk.CTkEntry] = {}
        for label, key, default in [
            ("服务器名称", "name", "管家婆云服务器"),
            ("远程号码（帮我吧/向日葵）", "remote", ""),
            ("Server Public IP", "ip", ""),
            ("Listen Port", "port", "51820"),
            ("Server VPN IP", "svpn", "10.66.66.1"),
            ("VPN Subnet", "subnet", "10.66.66.0/24"),
        ]:
            ctk.CTkLabel(
                fields_frame, text=label, font=ctk.CTkFont(size=13),
                anchor="w",
            ).pack(fill="x", pady=(10, 2))
            e = ctk.CTkEntry(fields_frame, font=ctk.CTkFont(size=13))
            if default:
                e.insert(0, default)
            e.pack(fill="x", pady=(0, 2))
            entries[key] = e

        self._new_srv_entries = entries

        btn_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        btn_frame.pack(pady=(20, 8))
        ctk.CTkButton(
            btn_frame, text="← 返回", width=100,
            command=self._home, font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(0, 12))
        self._new_srv_btn = ctk.CTkButton(
            btn_frame, text="Create", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._do_create_project,
        )
        self._new_srv_btn.pack(side="right")

    def _do_create_project(self) -> None:
        e = self._new_srv_entries
        name = e["name"].get().strip()
        ip = e["ip"].get().strip()
        if not name or not ip:
            messagebox.showwarning("Missing Fields", "Name and Public IP required.")
            return
        try:
            port = int(e["port"].get().strip() or "51820")
        except ValueError:
            messagebox.showwarning("Invalid Port", "Listen Port must be a number.")
            return

        self._new_srv_btn.configure(state="disabled", text="Creating…")
        threading.Thread(
            target=self._create_worker,
            args=(name, e["remote"].get().strip(), ip, port,
                  e["svpn"].get().strip(), e["subnet"].get().strip()),
            daemon=True,
        ).start()

    def _create_worker(self, name: str, remote: str, ip: str, port: int,
                       svpn: str, subnet: str) -> None:
        try:
            project = ProjectManager.create(name, ip, port, svpn, subnet,
                                             remote_number=remote)
            self.after(0, self._open_detail, project)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: (
                self._new_srv_btn.configure(state="normal", text="Create"),
                messagebox.showerror("Error", str(exc)),
            ))

    # ═══════════════════════════════════════════════════════════
    #  PROJECT LIST
    # ═══════════════════════════════════════════════════════════

    def _show_project_list(self) -> None:
        self._clear()
        ctk.CTkLabel(
            self._container, text="已有服务器项目",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(16, 12))

        names = ProjectManager.list_projects()
        if not names:
            ctk.CTkLabel(
                self._container,
                text="还没有项目，先新建一个吧 🌚",
                font=ctk.CTkFont(size=13),
                text_color="gray50",
            ).pack(pady=30)
        else:
            scroll = ctk.CTkScrollableFrame(
                self._container, corner_radius=8,
                height=340,
            )
            scroll.pack(fill="both", expand=True, padx=20)
            for n in names:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=4)
                ctk.CTkLabel(row, text=n, font=ctk.CTkFont(size=14)
                             ).pack(side="left")
                ctk.CTkButton(
                    row, text="Open", width=70,
                    font=ctk.CTkFont(size=12),
                    command=lambda name=n: self._open_detail(
                        ProjectManager.load(name)),
                ).pack(side="right")

        ctk.CTkButton(
            self._container, text="← 返回", width=100,
            command=self._home, font=ctk.CTkFont(size=13),
        ).pack(pady=(16, 8))

    # ═══════════════════════════════════════════════════════════
    #  PROJECT DETAIL
    # ═══════════════════════════════════════════════════════════

    def _open_detail(self, project: Project) -> None:
        self._current_project = project
        self._show_project_detail()

    def _show_project_detail(self) -> None:
        p = self._current_project
        if p is None:
            self._home()
            return

        self._clear()

        # Header
        hdr = ctk.CTkFrame(self._container, fg_color="transparent")
        hdr.pack(pady=(14, 4))
        ctk.CTkLabel(hdr, text=p.name, font=ctk.CTkFont(size=18, weight="bold")
                     ).pack(side="left")
        ctk.CTkButton(
            hdr, text="📁", width=32, height=28,
            font=ctk.CTkFont(size=13),
            command=lambda: open_folder(p.dir),
        ).pack(side="left", padx=(8, 0))

        # Info row
        info = ctk.CTkFrame(self._container, fg_color="transparent")
        info.pack(fill="x", padx=20, pady=(0, 10))
        for label, val in [
            ("公网", p.server_public_ip),
            ("VPN", p.server_vpn_ip),
            ("端口", str(p.listen_port)),
        ]:
            f = ctk.CTkFrame(info, fg_color="transparent")
            f.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11),
                         text_color="gray50").pack()
            ctk.CTkLabel(f, text=val, font=ctk.CTkFont(size=14, weight="bold")
                         ).pack()

        # Remote number — editable inline
        f = ctk.CTkFrame(info, fg_color="transparent")
        f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f, text="远程协助", font=ctk.CTkFont(size=11),
                     text_color="gray50").pack()
        re_frame = ctk.CTkFrame(f, fg_color="transparent")
        re_frame.pack()
        self._remote_entry = ctk.CTkEntry(
            re_frame, width=80, font=ctk.CTkFont(size=13),
            justify="center",
        )
        self._remote_entry.insert(0, p.remote_number)
        self._remote_entry.pack(side="left")
        ctk.CTkButton(
            re_frame, text="💾", width=28, height=24,
            font=ctk.CTkFont(size=11),
            command=lambda: self._save_remote(p),
        ).pack(side="left", padx=(4, 0))

        # Separator
        ctk.CTkLabel(self._container, text="─" * 40,
                     text_color="gray70", font=ctk.CTkFont(size=12)
                     ).pack(pady=(4, 8))

        ctk.CTkLabel(
            self._container, text=f"客户列表 ({len(p.clients)})",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20)

        # Client list
        scroll = ctk.CTkScrollableFrame(
            self._container, corner_radius=8, height=200,
        )
        scroll.pack(fill="x", padx=20, pady=(6, 12))
        if not p.clients:
            ctk.CTkLabel(scroll, text="暂无客户", text_color="gray50",
                         font=ctk.CTkFont(size=12)).pack(pady=16)
        else:
            for i, c in enumerate(p.clients, 1):
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=f"{i}.", font=ctk.CTkFont(size=12),
                             width=24).pack(side="left")
                ctk.CTkLabel(row, text=c.name, font=ctk.CTkFont(size=13),
                             anchor="w").pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(row, text=c.vpn_ip, font=ctk.CTkFont(size=12),
                             text_color="gray50", width=100
                             ).pack(side="left")
                ctk.CTkButton(
                    row, text="📁", width=32, height=24,
                    font=ctk.CTkFont(size=11),
                    command=lambda name=c.name: open_folder(p.dir / "clients" / name),
                ).pack(side="right")
                ctk.CTkButton(
                    row, text="✕", width=32, height=24,
                    fg_color="#b33", hover_color="#922",
                    font=ctk.CTkFont(size=11),
                    command=lambda name=c.name: self._do_remove_client(name),
                ).pack(side="right", padx=(6, 0))

        # Action buttons
        act = ctk.CTkFrame(self._container, fg_color="transparent")
        act.pack(fill="x", padx=20)

        ctk.CTkButton(
            act, text="← 返回", width=90,
            command=self._home, font=ctk.CTkFont(size=12),
        ).pack(side="left")

        ctk.CTkButton(
            act, text="新增客户",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b7a4b", hover_color="#1e5f38",
            command=self._do_add_client,
        ).pack(side="right", padx=(6, 0))

        # Status
        self._detail_status = ctk.CTkLabel(
            self._container, text="", font=ctk.CTkFont(size=11),
        )
        self._detail_status.pack(pady=(12, 4))

    # ── project detail actions ────────────────────────────────

    def _do_add_client(self) -> None:
        p = self._current_project
        if p is None:
            return

        base = ".".join(p.server_vpn_ip.split(".")[:3])
        used = {c.vpn_ip for c in p.clients} | {p.server_vpn_ip}
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

        self._set_status("Adding client…")
        threading.Thread(target=self._add_client_worker,
                         args=(name, ip or None), daemon=True).start()

    def _add_client_worker(self, name: str, ip: Optional[str]) -> None:
        p = self._current_project
        if p is None:
            return
        try:
            ProjectManager.add_client(p, name, ip)
            self.after(0, self._show_project_detail)
            self.after(0, lambda: self._set_status(f"✓ {name} added"))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: (
                self._set_status(f"✗ {exc}"),
                messagebox.showerror("Error", str(exc)),
            ))

    def _do_remove_client(self, name: str) -> None:
        p = self._current_project
        if p is None:
            return
        if not messagebox.askyesno("Confirm", f"Remove client '{name}'?"):
            return
        self._set_status(f"Removing {name}…")
        threading.Thread(target=self._remove_client_worker,
                         args=(name,), daemon=True).start()

    def _remove_client_worker(self, name: str) -> None:
        p = self._current_project
        if p is None:
            return
        try:
            ProjectManager.remove_client(p, name)
            self.after(0, self._show_project_detail)
            self.after(0, lambda: self._set_status(f"✓ {name} removed"))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: (
                self._set_status(f"✗ {exc}"),
                messagebox.showerror("Error", str(exc)),
            ))

    def _save_remote(self, p: Project) -> None:
        val = self._remote_entry.get().strip()
        p.remote_number = val
        ProjectManager.save(p)
        self._set_status("✓ 远程号码已保存")

    # ── bundled installer ──────────────────────────────────────

    @staticmethod
    def _bundled_installer() -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "wireguard-installer.exe")

    def _run_installer(self) -> None:
        path = self._bundled_installer()
        if os.path.exists(path):
            subprocess.Popen([path], shell=True)
            messagebox.showinfo(
                "安装",
                "WireGuard 安装程序已启动。\n安装完成后请重启本程序。",
            )

    def _set_status(self, text: str) -> None:
        if hasattr(self, "_detail_status"):
            self._detail_status.configure(text=text)
