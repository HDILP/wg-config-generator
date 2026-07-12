# GP Server Manager — Architecture

## Overview

```
main.py
  └─ app/          ← 主窗口 + 侧边栏 + 页面路由
       ├─ backup/  ← 可插拔备份引擎（ABC 接口）
       ├─ core/    ← 业务逻辑
       ├─ models/  ← 数据模型
       ├─ pages/   ← UI 页面（CTkFrame 子类）
       ├─ services/ ← 后端服务
       ├─ utils/   ← 文件 I/O
       └─ widgets/ ← 可复用组件
```

## Layers

### app/ — Application Shell
- `app.py`: GPServerManager (CTk). Grid 布局: sidebar | content.
- `theme.py`: Material You LIGHT/DARK palettes, applied via `ctk.set_appearance_mode`.

### backup/ — Backup Engine (Pluggable)
- `engine.py`: `BackupEngine` ABC. Methods: `create_plan`, `update_plan`, `delete_plan`, `enable`, `disable`, `query_status`, `probe`.
- `windows_task.py`: Adapter wrapping `services/backup_service.py`. Uses `schtasks.exe`.
- `maintenance_plan.py`: SQL Agent via `sp_add_job`/`sp_add_jobstep`/`sp_add_schedule`. Compatible SQL 2008–2022.
- `factory.py`: `get_engine(id)`, `list_engines()`, `probe_engines(instance)`.

### core/ — Business Logic
- `project_manager.py`: `ProjectManager` (static class). CRUD for projects + clients.
- `wg_keygen.py`: Shells out to `wg.exe` for keypair generation.
- `templates.py`: WireGuard `.conf` string templates.
- `qrcode_gen.py`: QR code from client config (qrcode[pil] or SVG fallback).

### models/ — Data
- `Project` wraps `ProjectSettings` (name, public_ip, vpn_ip, etc.), `KeyPair` (server keys), `List[ClientEntry]`.
- `BackupPolicy`: enabled, databases[], schedule_time, save_path, retention_days, compression.
- Serialization: `to_dict()` / `from_dict()` — project.json is the only source of truth.

### pages/ — UI Pages
Each page is a `CTkFrame` subclass constructed via `app._switch_to(PageClass, self, *args)`.

| Page | File | Key Sections |
|------|------|-------------|
| Home | `home_page.py` | New/Open/Recent |
| Dashboard | `dashboard_page.py` | Status + Security Score |
| Backup Center | `backup_page.py` | Quick Mode / History / Restore / Browser |
| WireGuard | `wireguard_page.py` | Server info + Client CRUD |
| SQL Server | `sql_page.py` | Port / Listen mode / Restart |
| Firewall | `firewall_page.py` | Service toggles + Custom port |
| Ops Info | `ops_page.py` | Editable ops form |
| Tools | `tools_page.py` | Ping / Trace / Public IP / Restart |
| Settings | `settings_page.py` | Theme / About |

### services/ — Backend Services
- `backup_service.py`: Immediate backup, history, file browser, health, cleanup.
- `sql_service.py`: SQL Server registry + SCM (PowerShell → cmd/reg.exe/sc.exe fallback).
- `firewall_service.py`: netsh advfirewall wrapper.
- `system_service.py`: ping, traceroute, public IP, system info.
- `wireguard_service.py`: `wg show` dump parser.

## Key Patterns

### Page switching
```python
# app.py
def _switch_to(self, page_class, *args, **kwargs):
    for w in self._content.winfo_children():
        w.destroy()
    page = page_class(self._content, *args, **kwargs)
    page.pack(fill="both", expand=True)
```

### Data flow (WireGuard)
```
UI click → ProjectManager.add_client(project, name)
         → generate_keypair()
         → _write_project()
              → project.json (JSON)
              → server.conf (template)
              → clients/<name>/client.conf (template)
              → clients/<name>/keys.json
              → clients/<name>/qrcode.png
```

### Data flow (Backup)
```
UI click → engine.create_plan(instance, policy)
         → WindowsTaskEngine:
              → generate .ps1 script
              → schtasks.exe /create
         → MaintenancePlanEngine:
              → sp_add_job / sp_add_jobstep / sp_add_schedule (T-SQL via .NET SqlClient)
```

## Cross-version Compatibility

| Component | SQL 2008 | SQL 2012 | SQL 2016 | SQL 2019 | SQL 2022 |
|-----------|----------|----------|----------|----------|----------|
| sp_add_job (Agent) | ✓ | ✓ | ✓ | ✓ | ✓ |
| SqlClient (.NET) | ✓ | ✓ | ✓ | ✓ | ✓ |
| schtasks.exe | Win7+ | Win7+ | Win7+ | Win10+ | Win10+ |
| PowerShell | Fallback | Fallback | ✓ | ✓ | ✓ |
