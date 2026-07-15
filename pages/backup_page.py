"""Backup Center page — quick mode, history, restore, browser."""
from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Dict, List, Optional

import customtkinter as ctk

from app.workspace import WorkspaceMode
from core.project_manager import ProjectManager
from models.backup import BackupPolicy
from models.project import Project
from backup import get_engine, list_engines, probe_engines, EngineStatus
from services.backup_service import (
    BackupHistoryEntry,
    check_compression_support,
    cleanup_old_backups,
    create_scheduled_task,
    get_backup_files,
    get_backup_health,
    get_backup_history,
    get_db_sizes,
    get_scheduled_task_status,
    immediate_backup,
    list_databases,
    list_sql_backup_jobs,
    remove_scheduled_task,
    restore_database,
)
from utils.file_ops import open_folder

if TYPE_CHECKING:
    from app.app import GPServerManager


class BackupCenterPage(ctk.CTkFrame):
    """Backup Center — one page, multiple sub-views (quick, history, restore, browser)."""
    WORKSPACE = WorkspaceMode.SERVER

    def __init__(self, master, app: GPServerManager, project: Optional[Project] = None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self._app = app
        self._project = project
        self._alive = True
        self._loaded_dbs: List[str] = []
        self._loaded_sizes: Dict[str, float] = {}
        self._compression_supported: bool = True
        self._immediate_running = False
        self._engine_var = ctk.StringVar(value="windows_task")
        self._engine_info: List[tuple] = []
        self._plan_exists = False
        self._mp_buttons: Dict[str, ctk.CTkButton] = {}
        self._build()

    def destroy(self) -> None:
        self._alive = False
        super().destroy()

    def refresh(self) -> None:
        if not self._project:
            return
        self._project = ProjectManager.load(self._project.name)
        self._clear()
        self._build()

    def _clear(self) -> None:
        self._alive = False
        for w in self.winfo_children():
            w.destroy()

    def _build(self) -> None:
        if not self._project:
            from types import SimpleNamespace
            from models.backup import BackupPolicy
            self._project = SimpleNamespace(
                name="",
                dir=Path("Projects/_server"),
                clients_dir=Path("Projects/_server/clients"),
                settings=SimpleNamespace(
                    backup=BackupPolicy(),
                    sql=SimpleNamespace(instance="MSSQLSERVER"),
                    name="Server",
                ),
                server_keypair=SimpleNamespace(public=""),
                clients=[],
            )
        policy = self._project.settings.backup

        # ── Header ────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(hdr, text="Backup Center", font=ctk.CTkFont(size=20, weight="bold"),
                     ).pack(side="left")
        ctk.CTkButton(hdr, text="🔄 刷新", width=70, height=28,
                       font=ctk.CTkFont(size=11),
                       command=self.refresh).pack(side="right", padx=(6, 0))
        ctk.CTkButton(hdr, text="📂 打开目录", width=90, height=28,
                       font=ctk.CTkFont(size=11),
                       command=lambda: open_folder(Path(policy.save_path)),
                       ).pack(side="right")

        # ── Sub-nav tabs ──────────────────────────────────────
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=24, pady=(4, 12))

        self._tab_var = ctk.StringVar(value="quick")
        tabs = [("极速模式", "quick"), ("历史记录", "history"),
                ("恢复", "restore"), ("备份浏览器", "browser")]
        for label, val in tabs:
            ctk.CTkRadioButton(tab_frame, text=label, variable=self._tab_var,
                               value=val, font=ctk.CTkFont(size=13),
                               command=self._switch_tab,
                               ).pack(side="left", padx=(0, 16))

        # ── Content container ──────────────────────────────────
        self._tab_content = ctk.CTkFrame(self, fg_color="transparent")
        self._tab_content.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        self._switch_tab()

    def _switch_tab(self) -> None:
        for w in self._tab_content.winfo_children():
            w.destroy()

        tab = self._tab_var.get()
        if tab == "quick":
            self._build_quick_mode()
        elif tab == "history":
            self._build_history()
        elif tab == "restore":
            self._build_restore()
        elif tab == "browser":
            self._build_browser()

    # ═══════════════════════════════════════════════════════════════
    #  Quick mode (default)
    # ═══════════════════════════════════════════════════════════════

    def _build_quick_mode(self) -> None:
        policy = self._project.settings.backup
        instance = self._project.settings.sql.instance
        container = ctk.CTkScrollableFrame(self._tab_content, corner_radius=0,
                                            fg_color="transparent")
        container.pack(fill="both", expand=True)

        # Health summary card
        self._health_card = ctk.CTkFrame(container, corner_radius=12)
        self._health_card.pack(fill="x", pady=(0, 12))

        health = get_backup_health(self._project)
        status_map = {"ok": "🟢  正常", "warning": "🟡  异常", "error": "🔴  失败", "unknown": "⚪  未知"}
        status_icon = {"ok": "#4CAF50", "warning": "#FF9800", "error": "#E53935", "unknown": "#9E9E9E"}
        hrow = ctk.CTkFrame(self._health_card, fg_color="transparent")
        hrow.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(hrow, text="备份状态",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkLabel(hrow, text=status_map.get(health.status, "未知"),
                     font=ctk.CTkFont(size=13),
                     text_color=status_icon.get(health.status, "#9E9E9E"),
                     ).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(hrow, text=f"最近成功: {health.last_success or '无'}",
                     font=ctk.CTkFont(size=11), text_color="#79747E",
                     ).pack(side="left", padx=(16, 0))
        ctk.CTkLabel(hrow, text=f"剩余磁盘: {health.remaining_gb}GB" if health.remaining_gb else "",
                     font=ctk.CTkFont(size=11), text_color="#79747E",
                     ).pack(side="right")

        # ═══ Engine selector ═══════════════════════════════════
        engine_card = ctk.CTkFrame(container, corner_radius=12)
        engine_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(engine_card, text="备份方式",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        self._engine_radio_frame = ctk.CTkFrame(engine_card, fg_color="transparent")
        self._engine_radio_frame.pack(fill="x", padx=16, pady=(0, 10))

        self._engine_var.trace_add("write", lambda *_: self._on_engine_change())
        threading.Thread(target=self._probe_engines_worker, args=(instance,),
                         daemon=True).start()

        self._engine_status_label = ctk.CTkLabel(
            engine_card, text="检测引擎中…",
            font=ctk.CTkFont(size=11), text_color="#79747E",
        )
        self._engine_status_label.pack(anchor="w", padx=16, pady=(0, 10))

        # ═══ Enable toggle ═════════════════════════════════════
        enable_frame = ctk.CTkFrame(container, corner_radius=12)
        enable_frame.pack(fill="x", pady=(0, 8))

        self._enable_var = ctk.BooleanVar(value=policy.enabled)
        ctk.CTkSwitch(enable_frame, text="启用自动备份",
                       variable=self._enable_var,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       command=self._toggle_enable,
                       ).pack(anchor="w", padx=16, pady=10)

        # ═══ Database selection ════════════════════════════════
        db_card = ctk.CTkFrame(container, corner_radius=12)
        db_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(db_card, text="备份数据库（可多选）",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 6))

        self._db_vars: Dict[str, ctk.BooleanVar] = {}
        db_frame = ctk.CTkFrame(db_card, fg_color="transparent")
        db_frame.pack(fill="x", padx=16, pady=(0, 8))

        self._db_status = ctk.CTkLabel(db_frame, text="加载数据库中…",
                                        font=ctk.CTkFont(size=11),
                                        text_color="#79747E")
        self._db_status.pack(anchor="w")

        # Load DBs in background
        threading.Thread(target=self._load_dbs_worker, args=(instance,),
                         daemon=True).start()

        # Size estimation
        self._size_label = ctk.CTkLabel(db_card, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color="#79747E")
        self._size_label.pack(anchor="w", padx=16, pady=(0, 8))

        # ═══ Schedule ═════════════════════════════════════════
        sched_card = ctk.CTkFrame(container, corner_radius=12)
        sched_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(sched_card, text="执行时间",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 2))

        sched_row = ctk.CTkFrame(sched_card, fg_color="transparent")
        sched_row.pack(fill="x", padx=16, pady=(4, 10))

        ctk.CTkLabel(sched_row, text="每天",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._hour_entry = ctk.CTkEntry(sched_row, width=50, font=ctk.CTkFont(size=13))
        self._hour_entry.insert(0, policy.schedule_time.split(":")[0])
        self._hour_entry.pack(side="left", padx=(8, 4))
        ctk.CTkLabel(sched_row, text="时",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._min_entry = ctk.CTkEntry(sched_row, width=50, font=ctk.CTkFont(size=13))
        self._min_entry.insert(0, policy.schedule_time.split(":")[1] if ":" in policy.schedule_time else "00")
        self._min_entry.pack(side="left", padx=(8, 4))
        ctk.CTkLabel(sched_row, text="分",
                     font=ctk.CTkFont(size=13)).pack(side="left")

        # ═══ Save path ═════════════════════════════════════════
        path_card = ctk.CTkFrame(container, corner_radius=12)
        path_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(path_card, text="保存目录",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 2))
        self._path_entry = ctk.CTkEntry(path_card, font=ctk.CTkFont(size=13))
        self._path_entry.insert(0, policy.save_path)
        self._path_entry.pack(fill="x", padx=16, pady=(4, 10))

        # ═══ Retention ════════════════════════════════════════
        ret_card = ctk.CTkFrame(container, corner_radius=12)
        ret_card.pack(fill="x", pady=(0, 8))

        ret_row = ctk.CTkFrame(ret_card, fg_color="transparent")
        ret_row.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(ret_row, text="保留时间",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(side="left")
        self._retention_entry = ctk.CTkEntry(ret_row, width=60, font=ctk.CTkFont(size=13))
        self._retention_entry.insert(0, str(policy.retention_days))
        self._retention_entry.pack(side="left", padx=(12, 4))
        ctk.CTkLabel(ret_row, text="天",
                     font=ctk.CTkFont(size=13)).pack(side="left")

        # ═══ Compression ══════════════════════════════════════
        comp_card = ctk.CTkFrame(container, corner_radius=12)
        comp_card.pack(fill="x", pady=(0, 8))

        self._comp_var = ctk.BooleanVar(value=policy.compression)
        self._comp_switch = ctk.CTkSwitch(
            comp_card, text="压缩备份（推荐）",
            variable=self._comp_var,
            font=ctk.CTkFont(size=13),
        )
        self._comp_switch.pack(anchor="w", padx=16, pady=(10, 2))

        self._comp_note = ctk.CTkLabel(
            comp_card,
            text="可节省约 50~80% 存储空间",
            font=ctk.CTkFont(size=11),
            text_color="#79747E",
        )
        self._comp_note.pack(anchor="w", padx=16, pady=(0, 10))

        # Check compression support in background
        threading.Thread(target=self._check_compression, args=(instance,),
                         daemon=True).start()

        # ═══ Actions ══════════════════════════════════════════
        act = ctk.CTkFrame(container, fg_color="transparent")
        act.pack(fill="x", pady=(12, 8))

        ctk.CTkButton(
            act, text="← 返回仪表盘", width=110,
            font=ctk.CTkFont(size=12),
            command=lambda: self._app.show_dashboard(),
        ).pack(side="left")

        self._immediate_btn = ctk.CTkButton(
            act, text="⚡ 立即备份",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b7a4b", hover_color="#1e5f38",
            command=self._do_immediate_backup,
        )
        self._immediate_btn.pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            act, text="📋 SQL 任务", width=90,
            font=ctk.CTkFont(size=11),
            command=self._show_sql_jobs,
        ).pack(side="right", padx=(6, 0))

        # Engine-specific action buttons (right side, before immediate)
        self._mp_action_frame = ctk.CTkFrame(act, fg_color="transparent")
        self._mp_action_frame.pack(side="right", padx=(6, 0))

        self._mp_buttons["create"] = ctk.CTkButton(
            self._mp_action_frame, text="创建", width=70,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6750A4", command=self._do_mp_create,
        )
        self._mp_buttons["update"] = ctk.CTkButton(
            self._mp_action_frame, text="更新", width=70,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#FF9800", command=self._do_mp_update,
        )
        self._mp_buttons["delete"] = ctk.CTkButton(
            self._mp_action_frame, text="删除", width=70,
            font=ctk.CTkFont(size=12), fg_color="#b33",
            hover_color="#922", command=self._do_mp_delete,
        )

        # Save (Windows Task)
        self._save_btn = ctk.CTkButton(
            act, text="💾 一键启用",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6750A4",
            command=self._save_policy,
        )
        self._save_btn.pack(side="right", padx=(6, 0))

        # Progress
        self._progress_frame = ctk.CTkFrame(container, fg_color="transparent")
        self._progress = ctk.CTkProgressBar(self._progress_frame, height=8)
        self._progress.set(0)
        self._progress_label = ctk.CTkLabel(self._progress_frame, text="",
                                             font=ctk.CTkFont(size=11),
                                             text_color="#79747E")

        # Status
        self._status = ctk.CTkLabel(container, text="",
                                     font=ctk.CTkFont(size=11),
                                     text_color="#79747E")
        self._status.pack(pady=(4, 8))

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _load_dbs_worker(self, instance: str) -> None:
        try:
            dbs = list_databases(instance)
            sizes = get_db_sizes(instance)
            self._loaded_dbs = dbs
            self._loaded_sizes = sizes
            self.after(0, self._render_db_list)
        except Exception as exc:
            self.after(0, lambda e=exc: self._db_status.configure(
                text=f"加载失败: {e}"))

    def _render_db_list(self) -> None:
        policy = self._project.settings.backup
        for w in self._db_status.master.winfo_children():
            if w != self._db_status:
                w.destroy()
        self._db_status.destroy()

        selected = set(policy.databases)
        # Pre-check: if no databases configured, default to all user DBs
        if not selected and self._enable_var.get():
            selected = set(self._loaded_dbs)

        self._db_vars.clear()
        for db in self._loaded_dbs:
            row = ctk.CTkFrame(self._db_status.master, fg_color="transparent")
            row.pack(fill="x", pady=2)

            var = ctk.BooleanVar(value=db in selected)
            cb = ctk.CTkCheckBox(row, text=db, variable=var,
                                  font=ctk.CTkFont(size=13),
                                  command=self._update_estimation)
            cb.pack(side="left")
            self._db_vars[db] = var

            # Last backup info
            history = self._get_latest_backup(db)
            if history:
                icon = "🟢" if history.get("status") == "success" else "🔴"
                ctk.CTkLabel(
                    row, text=f"{history.get('timestamp', '')[:16]}  {icon}",
                    font=ctk.CTkFont(size=10),
                    text_color="#79747E",
                ).pack(side="right")

        self._update_estimation()

    def _get_latest_backup(self, db: str) -> Optional[Dict]:
        from services.backup_service import _read_history
        entries = _read_history(self._project)
        for e in reversed(entries):
            if e.get("database") == db:
                return e
        return None

    def _update_estimation(self) -> None:
        total_mb = 0.0
        count = 0
        for db, var in self._db_vars.items():
            if var.get():
                total_mb += self._loaded_sizes.get(db, 0)
                count += 1
        comp_est = total_mb * 0.4 if self._comp_var.get() else total_mb
        self._size_label.configure(
            text=f"已选数据库: {count}    总大小: {total_mb:.1f} MB"
                 + (f"    预计压缩后: 约 {comp_est:.1f} MB" if self._comp_var.get() else "")
        )

    def _check_compression(self, instance: str) -> None:
        try:
            supported = check_compression_support(instance)
            self._compression_supported = supported
            if not supported:
                self.after(0, lambda: self._on_comp_result(supported))
        except Exception:
            pass

    def _on_comp_result(self, supported: bool) -> None:
        if not getattr(self, '_alive', False):
            return
        if not supported:
            self._comp_var.set(False)
            self._comp_switch.configure(state="disabled")
            self._comp_note.configure(
                text="当前 SQL Server 版本不支持压缩备份",
                text_color="#FF9800",
            )

    def _toggle_enable(self) -> None:
        pass  # applied on save

    def _save_policy(self) -> None:
        """Save backup policy to project.json and create/remove scheduled task."""
        policy = self._project.settings.backup

        # Read UI values
        policy.enabled = self._enable_var.get()
        policy.databases = [db for db, v in self._db_vars.items() if v.get()]
        policy.schedule_time = f"{self._hour_entry.get().strip()}:{self._min_entry.get().strip()}"
        policy.save_path = self._path_entry.get().strip()
        try:
            policy.retention_days = int(self._retention_entry.get().strip())
        except ValueError:
            messagebox.showwarning("错误", "保留天数必须是数字")
            return
        policy.compression = self._comp_var.get()

        # Save
        ProjectManager.save(self._project)

        if policy.enabled and policy.databases:
            self._progress_frame.pack(fill="x", padx=24, pady=(0, 8))
            threading.Thread(target=self._save_and_schedule, daemon=True).start()
        else:
            # Remove scheduled task
            remove_scheduled_task(self._project)
            self._set_status("✓ 策略已保存（自动备份已禁用）")

    def _save_and_schedule(self) -> None:
        self.after(0, lambda: (
            self._progress.pack(fill="x", pady=(0, 4)),
            self._progress_label.pack(),
            self._progress_label.configure(text="创建计划任务…"),
            self._progress.set(0.3),
        ))
        result = create_scheduled_task(self._project)
        self.after(0, lambda: (
            self._progress.set(1.0),
            self._progress_label.configure(
                text=f"✓ 计划任务已创建" if "SUCCESS" in result.upper() or "成功" in result
                     else f"✗ {result[:100]}"),
        ))
        self.after(2000, lambda: self._progress_frame.pack_forget())
        self._set_status("✓ 备份策略已保存")

    def _do_immediate_backup(self) -> None:
        if self._immediate_running:
            return

        selected = [db for db, v in self._db_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个数据库")
            return

        self._immediate_running = True
        self._immediate_btn.configure(state="disabled", text="备份中…")

        self._progress_frame.pack(fill="x", padx=24, pady=(0, 8))
        self._progress.pack(fill="x", pady=(0, 4))
        self._progress_label.pack()
        self._progress.set(0)

        threading.Thread(target=self._backup_worker, args=(selected,),
                         daemon=True).start()

    def _backup_worker(self, databases: List[str]) -> None:
        def progress(i: int, total: int, db: str) -> None:
            self.after(0, lambda: (
                self._progress.set(i / total),
                self._progress_label.configure(
                    text=f"[{i+1}/{total}] 正在备份 {db}…"),
            ))

        results = immediate_backup(self._project, databases, progress_cb=progress)

        self.after(0, lambda: self._progress.set(1.0))
        self.after(0, lambda: self._progress_label.configure(text="备份完成"))
        self.after(0, lambda: self._immediate_btn.configure(state="normal", text="⚡ 立即备份"))
        self._immediate_running = False

        # Show result summary
        ok = sum(1 for r in results if r.status == "success")
        fail = sum(1 for r in results if r.status == "failed")
        self._set_status(f"✓ 完成: {ok} 成功, {fail} 失败")
        if fail:
            errors = "\n".join(f"  {r.database}: {r.error[:60]}"
                               for r in results if r.status == "failed")
            messagebox.showwarning("备份结果",
                                   f"{fail} 个备份失败:\n{errors}")

        self.after(3000, lambda: self._progress_frame.pack_forget())

    # ═══════════════════════════════════════════════════════════════
    #  History tab
    # ═══════════════════════════════════════════════════════════════

    def _build_history(self) -> None:
        container = ctk.CTkScrollableFrame(self._tab_content, corner_radius=0,
                                            fg_color="transparent")
        container.pack(fill="both", expand=True)

        history = get_backup_history(self._project)
        if not history:
            ctk.CTkLabel(container, text="暂无备份记录",
                         font=ctk.CTkFont(size=13),
                         text_color="#79747E").pack(pady=30)
            ctk.CTkButton(container, text="← 返回极速模式", width=110,
                           font=ctk.CTkFont(size=12),
                           command=lambda: (self._tab_var.set("quick"), self._switch_tab()),
                           ).pack()
            return

        # Group by date
        current_date = ""
        for entry in history:
            ts = entry.get("timestamp", "")
            date_part = ts[:10] if ts else "未知"

            if date_part != current_date:
                current_date = date_part
                ctk.CTkLabel(container, text=date_part,
                             font=ctk.CTkFont(size=13, weight="bold"),
                             text_color="#6750A4",
                             ).pack(anchor="w", pady=(12, 4))

            # Entry card
            card = ctk.CTkFrame(container, corner_radius=8)
            card.pack(fill="x", pady=3)

            ok = entry.get("status") == "success"
            icon = "√" if ok else "×"
            icon_color = "#4CAF50" if ok else "#E53935"
            time_str = ts[11:16] if len(ts) >= 16 else ""

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)

            ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=icon_color, width=24).pack(side="left")
            ctk.CTkLabel(row, text=entry.get("database", ""),
                         font=ctk.CTkFont(size=13, weight="bold"),
                         width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=time_str, font=ctk.CTkFont(size=11),
                         text_color="#79747E", width=60).pack(side="left")

            if ok:
                ctk.CTkLabel(row, text=f"{entry.get('size_mb', 0):.0f}MB",
                             font=ctk.CTkFont(size=11), width=60,
                             text_color="#79747E").pack(side="left")
                ctk.CTkLabel(row, text=f"{entry.get('duration_sec', 0):.0f}秒",
                             font=ctk.CTkFont(size=11),
                             text_color="#79747E").pack(side="left")
            else:
                ctk.CTkLabel(row, text=entry.get("error", "失败")[:30],
                             font=ctk.CTkFont(size=10),
                             text_color="#E53935").pack(side="left", fill="x", expand=True)

    # ═══════════════════════════════════════════════════════════════
    #  Restore tab
    # ═══════════════════════════════════════════════════════════════

    def _build_restore(self) -> None:
        container = ctk.CTkFrame(self._tab_content, fg_color="transparent")
        container.pack(fill="both", expand=True)

        ctk.CTkLabel(container, text="恢复数据库",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     ).pack(anchor="w", pady=(0, 12))

        card = ctk.CTkFrame(container, corner_radius=12)
        card.pack(fill="x")

        # Backup file selection
        ctk.CTkLabel(card, text="选择备份文件",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(10, 4))

        # Get recent .bak files
        files = get_backup_files(self._project)
        file_names = [f.get("name", "") for f in files[:50]]

        self._restore_file_var = ctk.StringVar(value=file_names[0] if file_names else "")
        self._restore_file_menu = ctk.CTkOptionMenu(
            card, values=file_names or ["（无备份文件）"],
            variable=self._restore_file_var,
            font=ctk.CTkFont(size=12),
        )
        self._restore_file_menu.pack(fill="x", padx=16, pady=(4, 10))

        # Target database
        ctk.CTkLabel(card, text="恢复到",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     ).pack(anchor="w", padx=16, pady=(4, 4))

        self._restore_target_var = ctk.StringVar(value="original")
        ctk.CTkRadioButton(card, text="原数据库", variable=self._restore_target_var,
                           value="original", font=ctk.CTkFont(size=13),
                           ).pack(anchor="w", padx=16, pady=2)
        ctk.CTkRadioButton(card, text="新数据库", variable=self._restore_target_var,
                           value="new", font=ctk.CTkFont(size=13),
                           ).pack(anchor="w", padx=16, pady=2)

        self._new_db_entry = ctk.CTkEntry(card, font=ctk.CTkFont(size=13),
                                           placeholder_text="新数据库名称")
        self._new_db_entry.pack(fill="x", padx=16, pady=(4, 10))

        # Overwrite
        self._overwrite_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(card, text="覆盖已有数据库",
                        variable=self._overwrite_var,
                        font=ctk.CTkFont(size=13),
                        ).pack(anchor="w", padx=16, pady=(0, 10))

        # Action
        ctk.CTkButton(card, text="开始恢复",
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color="#FF9800", hover_color="#E68900",
                       command=self._do_restore,
                       ).pack(anchor="w", padx=16, pady=(0, 12))

        self._restore_status = ctk.CTkLabel(container, text="",
                                              font=ctk.CTkFont(size=11),
                                              text_color="#79747E")
        self._restore_status.pack(pady=(8, 4))

    def _do_restore(self) -> None:
        bak_name = self._restore_file_var.get()
        if not bak_name or bak_name.startswith("（"):
            messagebox.showwarning("提示", "请选择备份文件")
            return

        # Find full path
        files = get_backup_files(self._project)
        bak_path = ""
        for f in files:
            if f.get("name") == bak_name:
                bak_path = f.get("path", "")
                break

        if not bak_path:
            messagebox.showerror("错误", "找不到备份文件")
            return

        # Determine target database name
        target = ""
        if self._restore_target_var.get() == "original":
            # Extract original DB name from filename: DBName_YYYYMMDD.bak
            target = bak_name.rsplit("_", 1)[0]
        else:
            target = self._new_db_entry.get().strip()
            if not target:
                messagebox.showwarning("提示", "请输入新数据库名称")
                return

        self._restore_status.configure(text="正在恢复…")
        threading.Thread(target=self._restore_worker,
                         args=(bak_path, target, self._overwrite_var.get()),
                         daemon=True).start()

    def _restore_worker(self, bak_path: str, target: str, overwrite: bool) -> None:
        instance = self._project.settings.sql.instance
        result = restore_database(instance, bak_path, target, overwrite)
        self.after(0, lambda: self._restore_status.configure(
            text="✓ 恢复完成" if "error" not in result.lower() else f"✗ {result[:100]}")
        )

    # ═══════════════════════════════════════════════════════════════
    #  Backup Browser tab
    # ═══════════════════════════════════════════════════════════════

    def _build_browser(self) -> None:
        container = ctk.CTkFrame(self._tab_content, fg_color="transparent")
        container.pack(fill="both", expand=True)

        ctk.CTkLabel(container, text="备份浏览器",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     ).pack(anchor="w", pady=(0, 8))

        files = get_backup_files(self._project)
        if not files:
            ctk.CTkLabel(container, text="暂无备份文件",
                         font=ctk.CTkFont(size=13),
                         text_color="#79747E").pack(pady=20)
            return

        scroll = ctk.CTkScrollableFrame(container, corner_radius=12)
        scroll.pack(fill="both", expand=True)

        # Group by directory
        groups: Dict[str, list] = {}
        for f in files:
            dir_name = str(Path(f.get("relative", "")).parent)
            groups.setdefault(dir_name, []).append(f)

        for dir_name in sorted(groups.keys(), reverse=True):
            ctk.CTkLabel(scroll, text=f"📁  {dir_name}",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#6750A4",
                         ).pack(anchor="w", pady=(8, 2))

            for f in groups[dir_name]:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=2)

                ctk.CTkLabel(row, text=f.get("name", ""),
                             font=ctk.CTkFont(size=12),
                             anchor="w", width=250).pack(side="left")
                ctk.CTkLabel(row, text=f"{f.get('size_mb', 0):.1f}MB",
                             font=ctk.CTkFont(size=11),
                             text_color="#79747E", width=70).pack(side="left")
                ctk.CTkLabel(row, text=f.get("modified", "")[5:16],
                             font=ctk.CTkFont(size=10),
                             text_color="#79747E", width=100).pack(side="left")

    # ═══════════════════════════════════════════════════════════════
    #  Engine management
    # ═══════════════════════════════════════════════════════════════

    def _probe_engines_worker(self, instance: str) -> None:
        """Detect available engines and build radio buttons."""
        results = probe_engines(instance)
        self._engine_info = results

        self.after(0, lambda: self._render_engine_selector(results))

    def _render_engine_selector(self, results: list) -> None:
        if not getattr(self, '_alive', False):
            return
        for w in self._engine_radio_frame.winfo_children():
            w.destroy()

        first_available = ""
        for eid, name, err in results:
            disabled = err is not None
            rb = ctk.CTkRadioButton(
                self._engine_radio_frame, text=name,
                variable=self._engine_var, value=eid,
                font=ctk.CTkFont(size=13),
                state="disabled" if disabled else "normal",
            )
            rb.pack(side="left", padx=(0, 20))
            if not disabled and not first_available:
                first_available = eid

        if first_available:
            self._engine_var.set(first_available)
            self._engine_status_label.configure(
                text="" if not any(e[2] for e in results) else
                " ⚠ ".join(f"{e[1]}: {e[2]}" for e in results if e[2])
            )
        else:
            self._engine_var.set("windows_task")
            errors = [f"{e[1]}: {e[2]}" for e in results if e[2]]
            self._engine_status_label.configure(
                text="⚠ " + "; ".join(errors),
                text_color="#E53935",
            )

        self._on_engine_change()

    def _on_engine_change(self) -> None:
        """Show/hide buttons based on selected engine."""
        engine_id = self._engine_var.get()
        is_mp = engine_id == "maintenance_plan"

        # Show MP buttons or Windows Task save button
        if is_mp:
            self._mp_action_frame.pack(side="right", padx=(6, 0))
            self._save_btn.pack_forget()
            # Query MP status
            threading.Thread(target=self._query_mp_status,
                             daemon=True).start()
        else:
            self._mp_action_frame.pack_forget()
            self._save_btn.pack(side="right", padx=(6, 0))

    def _query_mp_status(self) -> None:
        instance = self._project.settings.sql.instance
        engine = get_engine("maintenance_plan")
        if not engine:
            return
        status = engine.query_status(instance)
        self._plan_exists = status.exists
        self.after(0, lambda: self._update_mp_buttons(status))

    def _update_mp_buttons(self, status) -> None:
        exists = status.exists
        self._mp_buttons["create"].pack_forget()
        self._mp_buttons["update"].pack_forget()
        self._mp_buttons["delete"].pack_forget()

        if not exists:
            self._mp_buttons["create"].pack(side="left", padx=2)
        else:
            self._mp_buttons["update"].pack(side="left", padx=2)
            self._mp_buttons["delete"].pack(side="left", padx=2)

        if exists:
            self._engine_status_label.configure(
                text=f"上次运行: {status.last_run or '无'}  "
                     f"结果: {'成功' if status.last_result == 'success' else '失败' if status.last_result == 'failed' else status.last_result}",
            )

    # ── MP actions ────────────────────────────────────────────

    def _get_policy_values(self):
        """Read current form values into a dict."""
        return {
            "databases": [db for db, v in self._db_vars.items() if v.get()],
            "schedule_time": f"{self._hour_entry.get().strip()}:{self._min_entry.get().strip()}",
            "save_path": self._path_entry.get().strip(),
            "retention_days": self._retention_entry.get().strip(),
            "compression": self._comp_var.get(),
        }

    def _do_mp_create(self) -> None:
        vals = self._get_policy_values()
        if not vals["databases"]:
            messagebox.showwarning("提示", "请至少选择一个数据库")
            return
        instance = self._project.settings.sql.instance

        def _work():
            engine = get_engine("maintenance_plan")
            if not engine:
                return
            result = engine.create_plan(
                instance, vals["databases"], vals["schedule_time"],
                vals["save_path"], int(vals["retention_days"]),
                vals["compression"],
            )
            self.after(0, lambda: self._set_status(result))
            self.after(0, lambda: self._on_engine_change())

        threading.Thread(target=_work, daemon=True).start()

    def _do_mp_update(self) -> None:
        vals = self._get_policy_values()
        if not vals["databases"]:
            messagebox.showwarning("提示", "请至少选择一个数据库")
            return
        instance = self._project.settings.sql.instance

        def _work():
            engine = get_engine("maintenance_plan")
            if not engine:
                return
            result = engine.update_plan(
                instance, vals["databases"], vals["schedule_time"],
                vals["save_path"], int(vals["retention_days"]),
                vals["compression"],
            )
            self.after(0, lambda: self._set_status(result))
            self.after(0, lambda: self._on_engine_change())

        threading.Thread(target=_work, daemon=True).start()

    def _do_mp_delete(self) -> None:
        if not messagebox.askyesno("确认", "确定删除 SQL Server 备份计划？"):
            return
        instance = self._project.settings.sql.instance

        def _work():
            engine = get_engine("maintenance_plan")
            if not engine:
                return
            result = engine.delete_plan(instance)
            self.after(0, lambda: self._set_status(result))
            self.after(0, lambda: self._on_engine_change())

        threading.Thread(target=_work, daemon=True).start()

    def _show_sql_jobs(self) -> None:
        """Open a dialog listing all SQL Agent jobs."""
        instance = self._project.settings.sql.instance if self._project else "MSSQLSERVER"
        top = ctk.CTkToplevel()
        top.title("SQL Server 代理作业")
        top.geometry("640x400")
        top.resizable(True, True)
        top.transient()
        top.grab_set()

        frame = ctk.CTkScrollableFrame(top)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        lbl = ctk.CTkLabel(frame, text="查询中…", font=ctk.CTkFont(size=11))
        lbl.pack(anchor="w")

        def _load():
            jobs = list_sql_backup_jobs(instance)
            lbl.after(0, lbl.destroy)
            if not jobs:
                ctk.CTkLabel(frame, text="未找到作业或无法连接",
                             font=ctk.CTkFont(size=12)).pack()
                return
            for j in jobs:
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=j["name"], font=ctk.CTkFont(size=13),
                             width=300, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=j["enabled"], font=ctk.CTkFont(size=11),
                             width=40, anchor="center",
                             text_color="#2b7a4b" if j["enabled"] == "是" else "#b33",
                             ).pack(side="left")
                ctk.CTkLabel(row, text=j["last_run"], font=ctk.CTkFont(size=11),
                             text_color="#79747E").pack(side="right")

        threading.Thread(target=_load, daemon=True).start()
