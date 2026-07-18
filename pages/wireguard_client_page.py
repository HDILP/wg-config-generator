"""WireGuard Client page — create configs, manage keys, export."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from utils.icon_loader import load_icon
from models.project import Project
from utils.file_ops import ensure_dir, open_folder, write_text

if TYPE_CHECKING:
    from app.app import GPServerManager


def _find_assets() -> Path:
    """Locate assets/installers/ — works in dev, Nuitka standalone, PyInstaller."""
    dev = Path(__file__).resolve().parent.parent / "assets" / "installers"
    for base in (
        Path(getattr(sys, "_MEIPASS", sys.executable)).parent,  # PyInstaller / Nuitka standalone
        Path(__file__).resolve().parent.parent,                 # dev
    ):
        p = base / "assets" / "installers"
        if p.is_dir():
            return p
    return dev


DEPLOY_INSTALLERS = _find_assets()
TUNSAFE_TAP_INSTALLER = DEPLOY_INSTALLERS / "TunSafe-TAP-9.21.2.exe"
TUNSAFE_INSTALLER = DEPLOY_INSTALLERS / "TunSafe-1.4.exe"
WIREGUARD_MSI = DEPLOY_INSTALLERS / "wireguard-amd64-1.1.msi"


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
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["on_surface"],
        ).pack(anchor="w", padx=PAD["xl"], pady=(PAD["lg"], PAD["md"]))

        if not self._project:
            ctk.CTkLabel(self, text="请先打开一个项目",
                         font=ctk.CTkFont(size=14),
                         text_color=C["outline"]).pack(pady=40)
            return

        s = self._project.settings

        # Server info
        info = ctk.CTkFrame(self, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        info.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))

        ctk.CTkLabel(info, text="服务器信息",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(anchor="w", padx=PAD["lg"], pady=(PAD["md"], PAD["sm"]))

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
                         text_color=C["outline"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Edit server conf
        edit_frame = ctk.CTkFrame(self, corner_radius=CR, fg_color=C["card_bg"], border_width=1, border_color=C["outline_variant"])
        edit_frame.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))
        ctk.CTkLabel(edit_frame, text="服务端配置",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(anchor="w", padx=PAD["lg"], pady=(PAD["md"], PAD["sm"]))
        row = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row.pack(fill="x", padx=PAD["lg"], pady=(0, PAD["md"]))
        ctk.CTkButton(row, text="📝 编辑 server.conf", height=32,
                       command=self._edit_server_conf).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="📂 打开目录", height=32,
                       command=lambda: open_folder(self._project.dir),
                       ).pack(side="left")

        # Client list
        ctk.CTkLabel(self, text=f"客户端 ({len(self._project.clients)})",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["on_surface"],
                     ).pack(anchor="w", padx=PAD["xl"], pady=(0, PAD["sm"]))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=CR, height=200,
                                         fg_color=C["card_bg"])
        scroll.pack(fill="x", padx=PAD["xl"], pady=(0, PAD["md"]))


        if not self._project.clients:
            ctk.CTkLabel(scroll, text="暂无客户端",
                         text_color=C["outline"],
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
                             text_color=C["outline"], width=100).pack(side="left")

                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right")
                ctk.CTkButton(btn_frame, text="",
                              image=load_icon("folder-open", 14, C["outline"]),
                              width=28, height=24,
                              command=lambda n=c.name: open_folder(
                                  self._project.dir / "clients" / n),
                              fg_color="transparent", hover_color=C["surface_variant"],
                              corner_radius=4,
                              ).pack(side="left", padx=2)
                ctk.CTkButton(btn_frame, text="",
                              image=load_icon("save", 14, C["outline"]),
                              width=28, height=24,
                              command=lambda n=c.name: self._export_qr(n),
                              fg_color="transparent", hover_color=C["surface_variant"],
                              corner_radius=4,
                              ).pack(side="left", padx=2)
                ctk.CTkButton(btn_frame, text="✕", width=28, height=24,
                              font=ctk.CTkFont(size=12),
                              fg_color="transparent",
                              hover_color="#FFEBEE", corner_radius=4,
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
                       ).pack(anchor="w", padx=PAD["xl"], pady=(8, 0))

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color=C["outline"])
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
            created = []
            self.after(0, lambda: self._set_status("生成中…"))
            try:
                for target, is_win7 in res:
                    self.after(0, lambda t=target, w7=is_win7: self._set_status(
                        f"打包 {t} ({'Win7' if w7 else 'Win10'})…"))
                    zip_name = self._generate_deploy(target, is_win7)
                    if zip_name:
                        created.append(zip_name)
                    else:
                        self.after(0, lambda t=target: self._set_status(f"✗ {t} 返回空"))
                if created:
                    deploy_dir = Path(__file__).resolve().parent.parent / "Deploy"
                    self.after(0, lambda: open_folder(deploy_dir))
                    self.after(0, lambda: self._set_status(
                        f"✓ 已生成 {len(created)} 个部署包"))
                else:
                    self.after(0, lambda: self._set_status("✗ 没有生成任何部署包"))
            except Exception as exc:
                error_text = str(exc)
                import traceback
                with open(Path.home() / "gpsm_deploy.log", "w", encoding="utf-8") as f:
                    f.write(traceback.format_exc())
                    f.write(f"\nassets dir: {DEPLOY_INSTALLERS}")
                    f.write(f"\nfiles: TunSafe={DEPLOY_INSTALLERS / 'TunSafe-1.4.exe'}")
                    f.write(f"\nTunSafe exists: {(DEPLOY_INSTALLERS / 'TunSafe-1.4.exe').is_file()}")
                self.after(0, lambda: self._set_status(
                    f"✗ 部署包生成失败：{error_text}"))
        threading.Thread(target=_work, daemon=True).start()

    def _generate_deploy(self, target: str, is_win7: bool) -> Optional[str]:
        """Generate a ZIP for one target (server or client name)."""
        import shutil, zipfile, tempfile

        p = self._project
        if not p:
            return

        tmp = Path(tempfile.mkdtemp(prefix="gp-deploy-"))
        try:
            os_label = "win7" if is_win7 else "win10"

            if target == "__server__":
                folder = tmp / "Server"
                folder.mkdir()
                write_text(folder / "server.conf", ProjectManager.export_server_conf(p))
                _copy_deploy_installers(folder, is_win7)
                write_text(folder / "README.txt",
                           f"""Server: {p.name}
IP: {p.settings.public_ip}
VPN: {p.settings.vpn_ip}
Port: {p.settings.listen_port}

1. {_install_instructions(is_win7)}
2. Import server.conf
3. Activate
""")
                zip_name = f"{p.name}_Server_{os_label}.zip"
            else:
                client = next((c for c in p.clients if c.name == target), None)
                if not client:
                    raise ValueError(f"客户端不存在：{target}")
                folder = tmp / "Client"
                folder.mkdir()
                cfg = ProjectManager.export_client_config(p, client.name)
                write_text(folder / "client.conf", cfg)
                _copy_deploy_installers(folder, is_win7)
                try:
                    from core.qrcode_gen import generate_qr_code
                    generate_qr_code(cfg, folder / "qrcode.png")
                except ImportError:
                    pass
                write_text(folder / "README.txt",
                           f"""{client.name}
VPN: {client.vpn_ip}
Server: {p.settings.public_ip}:{p.settings.listen_port}

1. {_install_instructions(is_win7)}
2. Import client.conf
3. Activate
""")
                zip_name = f"{p.name}_{client.name}_{os_label}.zip"

            deploy_dir = Path(__file__).resolve().parent.parent / "Deploy"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            zip_path = deploy_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in folder.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(tmp))
            return zip_name
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _copy_deploy_installers(target_dir: Path, is_win7: bool) -> None:
    """Copy the installer set matching the selected target OS."""
    if is_win7:
        files = (
            (TUNSAFE_TAP_INSTALLER, target_dir / TUNSAFE_TAP_INSTALLER.name),
            (TUNSAFE_INSTALLER, target_dir / TUNSAFE_INSTALLER.name),
        )
    else:
        files = ((WIREGUARD_MSI, target_dir / WIREGUARD_MSI.name),)

    missing = [str(src) for src, _ in files if not src.is_file()]
    if missing:
        raise FileNotFoundError("部署包缺少安装文件：" + ", ".join(missing))
    for src, dest in files:
        import shutil
        shutil.copy2(src, dest)


def _install_instructions(is_win7: bool) -> str:
    if is_win7:
        return "先安装 TunSafe-TAP-9.21.2.exe，再运行 TunSafe-1.4.exe"
    return "安装 wireguard-amd64-1.1.msi"


class _DeployDialog(ctk.CTkToplevel):
    """Pick targets + per-target OS. Each row: ☑ + name + OS radios."""

    def __init__(self, parent, project: Project):
        super().__init__(parent)
        self.title(f"生成部署包 — {project.name}")
        self.geometry("640x360")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="目标系统",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     ).pack(anchor="w", padx=20, pady=(16, 8))

        scroll = ctk.CTkScrollableFrame(self, height=180, corner_radius=8, fg_color=C["card_bg"])
        scroll.pack(fill="x", padx=20)

        self._rows: list[tuple[str, ctk.BooleanVar, ctk.StringVar]] = []

        def _deploy_row(target: str, label: str, default_checked: bool):
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=3)
            var = ctk.BooleanVar(value=default_checked)
            osv = ctk.StringVar(value="win10")
            ctk.CTkCheckBox(row, text=label, variable=var,
                            font=ctk.CTkFont(size=13),
                            ).pack(side="left")
            ctk.CTkRadioButton(row, text="Win10/11/Server2016+", variable=osv, value="win10",
                               ).pack(side="right", padx=(0, 4))
            ctk.CTkRadioButton(row, text="Win7/Server2012", variable=osv, value="win7",
                               ).pack(side="right", padx=(0, 18))
            return target, var, osv

        self._rows.append(_deploy_row("__server__", "服务器", True))
        for c in project.clients:
            self._rows.append(_deploy_row(c.name, c.name, False))

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
        self._name.pack(fill="x", padx=20, pady=(0, PAD["md"]))

        ctk.CTkLabel(self, text="VPN IP（留空自动分配）",
                     font=ctk.CTkFont(size=13), anchor="w",
                     ).pack(fill="x", padx=20, pady=(4, 4))
        self._ip = ctk.CTkEntry(self, font=ctk.CTkFont(size=13))
        self._ip.insert(0, suggested_ip)
        self._ip.pack(fill="x", padx=20, pady=(0, PAD["md"]))

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
