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

        ctk.CTkButton(self, text="📦 生成部署包", height=32,
                       font=ctk.CTkFont(size=12),
                       fg_color="#6750A4",
                       command=self._open_deploy_dialog,
                       ).pack(anchor="w", padx=24, pady=(8, 0))

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

    def _open_deploy_dialog(self) -> None:
        if not self._project:
            return
        dlg = _DeployDialog(self, self._project)
        self.wait_window(dlg)
        res = dlg.result()
        if res is None:
            return
        self._set_status("正在生成部署包…")
        def _work():
            for target, is_win7 in res:
                self._generate_deploy(target, is_win7)
        threading.Thread(target=_work, daemon=True).start()

    def _generate_deploy(self, target: str, is_win7: bool) -> None:
        """Generate a ZIP for one target (server or client name)."""
        from pathlib import Path
        import shutil, zipfile, tempfile

        p = self._project
        if not p:
            return

        tmp = Path(tempfile.mkdtemp())
        os_label = "win7" if is_win7 else "win10"

        if target == "server":
            folder = tmp / "Server"
            folder.mkdir()
            write_text(folder / "server.conf", ProjectManager.export_server_conf(p))
            installer_src = Path(__file__).resolve().parent.parent / "wireguard-installer.exe"
            if installer_src.exists():
                shutil.copy2(installer_src, folder / "WireGuard.exe")
            if is_win7:
                _write_win7_batch(folder)
                kbs_dir = Path(__file__).resolve().parent.parent / "assets" / "kbs"
                if kbs_dir.exists():
                    for f in kbs_dir.iterdir():
                        if f.suffix == ".msu":
                            shutil.copy2(f, folder)
            write_text(folder / "README.txt",
                       f"""Server: {p.name}
IP: {p.settings.public_ip}
VPN: {p.settings.vpn_ip}
Port: {p.settings.listen_port}

1. {"install_win7.bat → restart" if is_win7 else "Install WireGuard"}
2. Import server.conf
3. Activate
""")
            zip_name = f"{p.name}_Server_{os_label}.zip"
        else:
            client = next((c for c in p.clients if c.name == target), None)
            if not client:
                return
            folder = tmp / "Client"
            folder.mkdir()
            cfg = ProjectManager.export_client_config(p, client.name)
            write_text(folder / "client.conf", cfg)
            installer_src = Path(__file__).resolve().parent.parent / "wireguard-installer.exe"
            if installer_src.exists():
                shutil.copy2(installer_src, folder / "WireGuard.exe")
            if is_win7:
                _write_win7_batch(folder)
                kbs_dir = Path(__file__).resolve().parent.parent / "assets" / "kbs"
                if kbs_dir.exists():
                    for f in kbs_dir.iterdir():
                        if f.suffix == ".msu":
                            shutil.copy2(f, folder)
            try:
                from core.qrcode_gen import generate_qr_code
                generate_qr_code(cfg, folder / "qrcode.png")
            except ImportError:
                pass
            write_text(folder / "README.txt",
                       f"""{client.name}
VPN: {client.vpn_ip}
Server: {p.settings.public_ip}:{p.settings.listen_port}

1. {"install_win7.bat → restart" if is_win7 else "Install WireGuard"}
2. Import client.conf
3. Activate
""")
            zip_name = f"{p.name}_{client.name}_{os_label}.zip"

        deploy_dir = Path("Deploy")
        deploy_dir.mkdir(exist_ok=True)
        zip_path = deploy_dir / zip_name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in folder.rglob("*"):
                zf.write(f, f.relative_to(tmp))

        shutil.rmtree(tmp, ignore_errors=True)

        self.after(0, lambda: open_folder(deploy_dir))
        self.after(0, lambda: self._set_status(f"✓ {zip_name}"))



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

:: 安装补丁文件
if "%KB1_DONE%"=="0" if exist "%~dp0KB2921916.msu" (
    echo 安装 KB2921916...
    wusa "%~dp0KB2921916.msu" /quiet /norestart
    set "KB1_DONE=1"
)

if "%KB2_DONE%"=="0" (
    echo 下载 KB3033929...
    bitsadmin /transfer "KB3033929" /download /priority high "https://download.microsoft.com/download/c/8/7/c87ae67e-a228-48fb-8f02-b2a9a1238099/Windows6.1-KB3033929-x64.msu" "%TEMP%\\KB3033929.msu" >nul 2>&1
    if exist "%TEMP%\\KB3033929.msu" (
        echo 安装 KB3033929...
        wusa "%TEMP%\\KB3033929.msu" /quiet /norestart
    )
)

echo.
echo ===== 安装完成 =====
echo 请重启计算机后再安装 WireGuard。
echo.
pause
""")


class _DeployDialog(ctk.CTkToplevel):
    """Pick targets + per-target OS. Each row: ☑ + name + OS radios."""

    def __init__(self, parent, project: Project):
        super().__init__(parent)
        self.title(f"生成部署包 — {project.name}")
        self.geometry("400x340")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="目标系统",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=20, pady=(16, 8))

        scroll = ctk.CTkScrollableFrame(self, height=180, corner_radius=8)
        scroll.pack(fill="x", padx=20)

        # Header row
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="", width=30).pack(side="left")
        ctk.CTkLabel(hdr, text="目标", font=ctk.CTkFont(size=11, weight="bold"),
                     anchor="w", width=120).pack(side="left")
        ctk.CTkLabel(hdr, text="Win10/11+", font=ctk.CTkFont(size=10),
                     width=80).pack(side="right")
        ctk.CTkLabel(hdr, text="Win7/2012", font=ctk.CTkFont(size=10),
                     width=80).pack(side="right")

        self._rows: list[tuple[str, ctk.BooleanVar, ctk.StringVar]] = []

        # Server row
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=3)
        sv = ctk.BooleanVar(value=True)
        osv = ctk.StringVar(value="win10")
        ctk.CTkCheckBox(row, text="", variable=sv).pack(side="left")
        ctk.CTkLabel(row, text="服务器", font=ctk.CTkFont(size=13),
                     anchor="w", width=120).pack(side="left")
        ctk.CTkRadioButton(row, text="", variable=osv, value="win10",
                           ).pack(side="right", padx=(0, 18))
        ctk.CTkRadioButton(row, text="", variable=osv, value="win7",
                           ).pack(side="right", padx=(0, 18))
        self._rows.append(("server", sv, osv))

        for c in project.clients:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            cv = ctk.BooleanVar(value=False)
            cosv = ctk.StringVar(value="win10")
            ctk.CTkCheckBox(row, text="", variable=cv).pack(side="left")
            ctk.CTkLabel(row, text=c.name, font=ctk.CTkFont(size=13),
                         anchor="w", width=120).pack(side="left")
            ctk.CTkRadioButton(row, text="", variable=cosv, value="win10",
                               ).pack(side="right", padx=(0, 18))
            ctk.CTkRadioButton(row, text="", variable=cosv, value="win7",
                               ).pack(side="right", padx=(0, 18))
            self._rows.append((c.name, cv, cosv))

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(fill="x", padx=20, pady=(12, 12))
        ctk.CTkButton(btn_f, text="取消", width=80,
                       command=self.destroy,
                       font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_f, text="生成", command=self._confirm,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       fg_color="#6750A4").pack(side="right")

        self._confirmed = False

    def _confirm(self) -> None:
        selected = [(name, osv.get() == "win7")
                    for name, cv, osv in self._rows if cv.get()]
        if not selected:
            from tkinter import messagebox
            messagebox.showwarning("提示", "请至少选择一个目标", parent=self)
            return
        self._confirmed = True
        self._result = selected
        self.destroy()

    def result(self):
        return self._result if self._confirmed else None


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
