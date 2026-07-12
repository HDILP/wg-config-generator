"""WireGuard Client page — create configs, manage keys, export."""
from __future__ import annotations

import threading
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.project import Project
from utils.file_ops import ensure_dir, open_folder, write_text

if TYPE_CHECKING:
    from app.app import GPServerManager


class WireGuardClientPage(ctk.CTkFrame):
    """Client-mode WireGuard: config generation, client CRUD, export."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project: Optional[Project] = None
        self._build()

    def _build(self) -> None:
        self._project = self._app.get_current_project()

        ctk.CTkLabel(
            self, text="WireGuard 配置",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        if not self._project:
            ctk.CTkLabel(self, text="请先打开一个项目",
                         font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=40)
            return

        s = self._project.settings

        # Server info
        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(info, text="服务器信息",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        for label, val in [
            ("公网 IP", s.public_ip or "未设置"),
            ("VPN 地址", f"{s.vpn_ip}/24"),
            ("监听端口", str(s.listen_port)),
            ("公钥", (self._project.server_keypair.public[:32] + "..."
                      if self._project.server_keypair.public else "未生成")),
        ]:
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12),
                         text_color="#79747E", width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Edit server conf
        edit_frame = ctk.CTkFrame(self, corner_radius=12)
        edit_frame.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(edit_frame, text="服务端配置",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))
        row = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkButton(row, text="📝 编辑 server.conf", height=32,
                       command=self._edit_server_conf).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="📂 打开目录", height=32,
                       command=lambda: open_folder(self._project.dir),
                       ).pack(side="left")

        # Client list
        ctk.CTkLabel(self, text=f"客户端 ({len(self._project.clients)})",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=24, pady=(8, 6))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12, height=200)
        scroll.pack(fill="x", padx=24, pady=(0, 12))


        if not self._project.clients:
            ctk.CTkLabel(scroll, text="暂无客户端",
                         text_color="#79747E",
                         font=ctk.CTkFont(size=12)).pack(pady=20)
        else:
            for i, c in enumerate(self._project.clients, 1):
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=8)

                ctk.CTkLabel(row, text=f"{i}.", font=ctk.CTkFont(size=12),
                             width=24).pack(side="left")
                ctk.CTkLabel(row, text=c.name, font=ctk.CTkFont(size=13),
                             anchor="w", width=120).pack(side="left")
                ctk.CTkLabel(row, text=c.vpn_ip, font=ctk.CTkFont(size=12),
                             text_color="#79747E", width=100).pack(side="left")

                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right")
                ctk.CTkButton(btn_frame, text="📁", width=28, height=24,
                              font=ctk.CTkFont(size=10),
                              command=lambda n=c.name: open_folder(
                                  self._project.dir / "clients" / n),
                              ).pack(side="left", padx=2)
                ctk.CTkButton(btn_frame, text="📱", width=28, height=24,
                              font=ctk.CTkFont(size=10),
                              command=lambda n=c.name: self._export_qr(n),
                              ).pack(side="left", padx=2)
                ctk.CTkButton(btn_frame, text="✕", width=28, height=24,
                              fg_color="#b33", hover_color="#922",
                              font=ctk.CTkFont(size=10),
                              command=lambda n=c.name: self._remove_client(n),
                              ).pack(side="left", padx=2)

        # Actions
        act = ctk.CTkFrame(self, fg_color="transparent")
        act.pack(fill="x", padx=24)

        ctk.CTkButton(act, text="← 返回仪表盘", width=110,
                       font=ctk.CTkFont(size=12),
                       command=lambda: self._app.show_dashboard(),
                       ).pack(side="left")

        ctk.CTkButton(act, text="＋ 新增客户端",
                       font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color="#2b7a4b",
                       command=self._add_client,
                       ).pack(side="right")

        # Target OS + deploy button
        os_frame = ctk.CTkFrame(self, fg_color="transparent")
        os_frame.pack(fill="x", padx=24, pady=(8, 0))
        self._os_var = ctk.StringVar(value="win10")
        ctk.CTkRadioButton(os_frame, text="Win10/11", variable=self._os_var,
                           value="win10", font=ctk.CTkFont(size=11),
                           ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(os_frame, text="Win7", variable=self._os_var,
                           value="win7", font=ctk.CTkFont(size=11),
                           ).pack(side="left")

        ctk.CTkButton(os_frame, text="📦 生成部署包", height=32,
                       font=ctk.CTkFont(size=12),
                       fg_color="#6750A4",
                       command=self._generate_deploy,
                       ).pack(side="right")

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(8, 4))

    def refresh(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _edit_server_conf(self) -> None:
        if not self._project:
            return
        path = self._project.dir / "server.conf"
        if path.exists():
            # ponytail: open in notepad on Windows
            import subprocess, sys as _sys
            _sys.platform == "win32" and subprocess.Popen(["notepad", str(path)])
            self._set_status("已打开 server.conf")

    def _add_client(self) -> None:
        if not self._project:
            return
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
        self._set_status(f"Adding {name}…")
        threading.Thread(target=self._add_worker, args=(name, ip or None),
                         daemon=True).start()

    def _add_worker(self, name: str, ip: Optional[str]) -> None:
        try:
            self._project = ProjectManager.add_client(self._project, name, ip)
            self.after(0, self.refresh)
            self.after(0, lambda: self._set_status(f"✓ {name} added"))
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"✗ {exc}"))

    def _remove_client(self, name: str) -> None:
        if not messagebox.askyesno("确认", f"确定删除客户端 '{name}'？"):
            return
        self._set_status(f"Removing {name}…")
        threading.Thread(target=self._remove_worker, args=(name,),
                         daemon=True).start()

    def _remove_worker(self, name: str) -> None:
        try:
            ProjectManager.remove_client(self._project, name)
            self._project = ProjectManager.load(self._project.name)
            self.after(0, self.refresh)
            self.after(0, lambda: self._set_status(f"✓ {name} removed"))
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"✗ {exc}"))

    def _export_qr(self, name: str) -> None:
        try:
            cfg = ProjectManager.export_client_config(self._project, name)
            path = self._project.dir / "clients" / name / "qrcode.png"
            if path.exists():
                open_folder(path.parent)
                self._set_status(f"✓ QR code for {name}")
            else:
                from core.qrcode_gen import generate_qr_code
                generate_qr_code(cfg, path)
                open_folder(path.parent)
                self._set_status(f"✓ QR code generated for {name}")
        except Exception as exc:
            self._set_status(f"✗ {exc}")

    def _generate_deploy(self) -> None:
        """One-click deploy package: Deploy/<name>/Server/ + Client/."""
        from pathlib import Path
        import shutil
        import platform

        p = self._project
        if not p:
            return
        is_win7 = hasattr(self, '_os_var') and self._os_var.get() == "win7"
        deploy_dir = Path("Deploy") / p.name
        server_dir = ensure_dir(deploy_dir / "Server")
        client_base = ensure_dir(deploy_dir / "Client")

        # Write server.conf
        write_text(server_dir / "server.conf",
                   ProjectManager.export_server_conf(p))

        # Copy WireGuard installer
        installer_src = Path(__file__).resolve().parent.parent / "wireguard-installer.exe"
        if installer_src.exists():
            shutil.copy2(installer_src, server_dir / "WireGuard.exe")

        if is_win7:
            _write_win7_batch(server_dir)
            # Copy KB patches if available
            kbs_dir = Path(__file__).resolve().parent.parent / "assets" / "kbs"
            if kbs_dir.exists():
                for f in kbs_dir.iterdir():
                    if f.suffix in (".msu", ".exe"):
                        shutil.copy2(f, server_dir)
                        for c in p.clients:
                            shutil.copy2(f, client_base / c.name)

        # Server README
        write_text(server_dir / "README_Server.txt",
                   f"""GP Server Manager — 部署包
===========================
项目: {p.name}
公网 IP: {p.settings.public_ip}
VPN 地址: {p.settings.vpn_ip}
监听端口: {p.settings.listen_port}
目标系统: {"Windows 7" if is_win7 else "Windows 10/11"}

服务器部署步骤:
1. {"运行 install_win7.bat（自动安装补丁）" if is_win7 else "安装 WireGuard（如已安装可跳过）"}
2. 打开 WireGuard → 导入 server.conf
3. 激活隧道
4. 设置为 Tunnel Service（可选）

生成时间: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}
""")

        # Per-client files
        for c in p.clients:
            c_out = ensure_dir(client_base / c.name)
            cfg = ProjectManager.export_client_config(p, c.name)
            write_text(c_out / "client.conf", cfg)
            if installer_src.exists():
                shutil.copy2(installer_src, c_out / "WireGuard.exe")
            if is_win7:
                _write_win7_batch(c_out)
            write_text(c_out / "README_Client.txt",
                       f"""{c.name}
====================
VPN IP: {c.vpn_ip}
服务器: {p.settings.public_ip}:{p.settings.listen_port}

客户端部署步骤:
1. 安装 WireGuard（如已安装可跳过）
2. 双击 client.conf 或打开 WireGuard → 导入
3. 激活

服务器公钥: {p.server_keypair.public}
""")
            # QR code
            try:
                from core.qrcode_gen import generate_qr_code
                generate_qr_code(cfg, c_out / "qrcode.png")
            except ImportError:
                pass

        open_folder(deploy_dir)
        self._set_status(f"✓ 部署包已生成: {deploy_dir}")


def _write_win7_batch(target_dir) -> None:
    """Write install_win7.bat — checks KBs, downloads & installs missing ones."""
    from pathlib import Path
    write_text(target_dir / "install_win7.bat", """@echo off
chcp 65001 >nul
title WireGuard Win7 补丁安装
echo ═══════════════════════════════════════
echo   WireGuard Windows 7 补丁安装工具
echo ═══════════════════════════════════════
echo.

:: Check KB2921916
reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\Packages\\Package_for_KB2921916~*" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] KB2921916 已安装
    set "KB1_DONE=1"
) else (
    echo [✗] KB2921916 未安装
    set "KB1_DONE=0"
)

:: Check KB3033929
reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\Packages\\Package_for_KB3033929~*" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] KB3033929 已安装
    set "KB2_DONE=1"
) else (
    echo [✗] KB3033929 未安装
    set "KB2_DONE=0"
)

echo.

if "%KB1_DONE%"=="1" if "%KB2_DONE%"=="1" (
    echo 所有补丁已安装，可直接安装 WireGuard。
    pause
    exit /b 0
)

:: 尝试本地补丁文件
if "%KB1_DONE%"=="0" if exist "%~dp0KB2921916.msu" (
    echo 安装 KB2921916（本地文件）...
    wusa "%~dp0KB2921916.msu" /quiet /norestart
    set "KB1_DONE=1"
)
if "%KB2_DONE%"=="0" if exist "%~dp0KB3033929.msu" (
    echo 安装 KB3033929（本地文件）...
    wusa "%~dp0KB3033929.msu" /quiet /norestart
    set "KB2_DONE=1"
)

:: 在线下载（后备）
set "URL1=https://download.wireguard.com/windows-toolchain/distfiles/Windows6.1-KB2921916-x64.msu"
set "URL2=https://download.microsoft.com/download/c/8/7/c87ae67e-a228-48fb-8f02-b2a9a1238099/Windows6.1-KB3033929-x64.msu"

if "%KB1_DONE%"=="0" (
    echo 下载 KB2921916...
    bitsadmin /transfer "KB2921916" /download /priority high "%URL1%" "%TEMP%\\KB2921916.msu" >nul 2>&1
    if exist "%TEMP%\\KB2921916.msu" (
        wusa "%TEMP%\\KB2921916.msu" /quiet /norestart
    )
)
if "%KB2_DONE%"=="0" (
    echo 下载 KB3033929...
    bitsadmin /transfer "KB3033929" /download /priority high "%URL2%" "%TEMP%\\KB3033929.msu" >nul 2>&1
    if exist "%TEMP%\\KB3033929.msu" (
        wusa "%TEMP%\\KB3033929.msu" /quiet /norestart
    )
)

echo.
echo ===== 安装完成 =====
echo 请重启计算机后再安装 WireGuard。
echo.
pause
""")

class _AddClientDialog(ctk.CTkToplevel):
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
