"""Live WireGuard status and safe hand-off to the official client."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.wg_keygen import check_wg_available
from services.wireguard_service import wg_interfaces, wg_show
from widgets import Card, PrimaryButton

if TYPE_CHECKING:
    from app.app import GPServerManager

WG_DIR = Path("C:/Program Files/WireGuard")
WG_INSTALLER = (Path(__file__).resolve().parent.parent / "assets" / "installers"
                / "wireguard-amd64-1.1.msi")


class WireGuardServerPage(ctk.CTkFrame):
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, project=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app, self._project = app, project
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="WireGuard", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=24, pady=(20, 4))
        self._summary = ctk.CTkLabel(self, text="Checking WireGuard...", text_color="#79747E")
        self._summary.pack(anchor="w", padx=24, pady=(0, 12))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 10))
        PrimaryButton(actions, text="Open WireGuard", command=self._open_client).pack(side="left")
        PrimaryButton(actions, text="Open configuration folder", command=self._open_config).pack(side="left", padx=8)
        PrimaryButton(actions, text="Refresh", command=self._refresh).pack(side="right")
        if WG_INSTALLER.exists():
            self._install = PrimaryButton(actions, text="Install WireGuard", command=self._install_wireguard)
            self._install.pack(side="left", padx=8)
        self._details = ctk.CTkTextbox(self, corner_radius=12, font=ctk.CTkFont(family="Consolas", size=12))
        self._details.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self._details.configure(state="disabled")
        self._refresh()

    def _refresh(self) -> None:
        self._summary.configure(text="Checking live tunnels...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        error = check_wg_available()
        if error:
            self.after(0, lambda: self._show("WireGuard is not installed or wg.exe is unavailable.\n\n" + error, False))
            return
        try:
            interfaces = wg_interfaces()
            lines = []
            for interface in interfaces:
                info = wg_show(interface)
                lines.append(f"[{interface}]  listen port: {info.listen_port}  peers: {len(info.peers)}")
                for peer in info.peers:
                    endpoint = peer.endpoint or "no endpoint"
                    handshake = peer.latest_handshake or "no handshake"
                    lines.append(f"  {peer.public_key[:16]}...  {endpoint}  {handshake}")
            text = "\n".join(lines) if lines else "No active WireGuard tunnels. Import and activate a tunnel in the official WireGuard client."
            self.after(0, lambda: self._show(text, True))
        except Exception as exc:
            self.after(0, lambda: self._show(f"Unable to read WireGuard status:\n{exc}", False))

    def _show(self, text: str, healthy: bool) -> None:
        self._summary.configure(text="WireGuard available" if healthy else "WireGuard unavailable", text_color="#4CAF50" if healthy else "#B3261E")
        self._details.configure(state="normal")
        self._details.delete("1.0", "end")
        self._details.insert("1.0", text)
        self._details.configure(state="disabled")

    @staticmethod
    def _open_client() -> None:
        executable = WG_DIR / "wireguard.exe"
        if executable.exists():
            subprocess.Popen([str(executable)])
        else:
            messagebox.showwarning("WireGuard", "WireGuard is not installed.")

    @staticmethod
    def _open_config() -> None:
        directory = WG_DIR / "data" / "configurations"
        if directory.exists():
            subprocess.Popen(["explorer", str(directory)])
        else:
            messagebox.showwarning("WireGuard", "The WireGuard configuration directory does not exist yet.")

    @staticmethod
    def _install_wireguard() -> None:
        subprocess.Popen(["msiexec.exe", "/i", str(WG_INSTALLER)])
