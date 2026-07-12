"""Deployment page — package and export deployment configs (Client Mode)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from utils.file_ops import open_folder

if TYPE_CHECKING:
    from app.app import GPServerManager


class DeploymentPage(ctk.CTkFrame):
    """Deployment package management: export configs, create deployment bundles."""
    WORKSPACE = WorkspaceMode.CLIENT

    def __init__(self, master, app: GPServerManager, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="部署资料",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        proj = ProjectManager.list_projects()

        if not proj:
            ctk.CTkLabel(self, text="暂无项目",
                         font=ctk.CTkFont(size=14),
                         text_color="#79747E").pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(self, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        for pname in reversed(proj):
            try:
                project = ProjectManager.load(pname)
            except Exception:
                continue

            card = ctk.CTkFrame(scroll, corner_radius=8)
            card.pack(fill="x", pady=4)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=10)

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(text_frame, text=f"📦  {pname}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(text_frame,
                         text=f"{len(project.clients)} 个客户端  ·  {project.settings.public_ip or '未设置IP'}",
                         font=ctk.CTkFont(size=11),
                         text_color="#79747E",
                         anchor="w").pack(fill="x")

            ctk.CTkButton(
                row, text="📂 打开目录", width=90, height=28,
                font=ctk.CTkFont(size=11),
                command=lambda d=project.dir: open_folder(d),
            ).pack(side="right", padx=(6, 0))
            ctk.CTkButton(
                row, text="📱 导出二维码", width=90, height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#6750A4",
                command=lambda n=pname: self._export_all_qr(n),
            ).pack(side="right")

    def _export_all_qr(self, pname: str) -> None:
        try:
            project = ProjectManager.load(pname)
            for c in project.clients:
                cfg = ProjectManager.export_client_config(project, c.name)
                qr_path = project.dir / "clients" / c.name / "qrcode.png"
                from core.qrcode_gen import generate_qr_code
                generate_qr_code(cfg, qr_path)
            open_folder(project.dir / "clients")
            self._set_status(f"✓ {pname}: 二维码已生成")
        except Exception as exc:
            self._set_status(f"✗ {exc}")

    def _set_status(self, text: str) -> None:
        # ponytail: use label if needed
        pass
