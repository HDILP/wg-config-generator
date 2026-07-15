# GP Server Manager — Architecture

## Overview

```
启动 → WorkspaceLauncher → Server Mode / Client Mode
  Server Mode: 服务器本机操作（SQL/WireGuard/防火墙/备份/服务/系统信息）
  Client Mode: 运维电脑操作（项目/客户/WireGuard配置/部署包/运维信息）

每页声明 WORKSPACE = SERVER / CLIENT / BOTH
app.py 根据 mode 自动切换侧边栏 + 过滤页面路由
```

```
main.py
  └─ app/          ← 主窗口 + 侧边栏 + 页面路由 + workspace 选择
       ├─ backup/  ← 可插拔备份引擎（ABC 接口）
       ├─ core/    ← 业务逻辑
       ├─ models/  ← 数据模型
       ├─ pages/   ← UI 页面（CTkFrame 子类）
       ├─ services/ ← 后端服务
       ├─ utils/   ← 文件 I/O
       └─ widgets/ ← 可复用 UI 组件（Button/Card/FieldRow/Toast/Icons/AutoDisable）
```

## Layers

### app/ — Application Shell
- `app.py`: GPServerManager (CTk). Grid 布局: sidebar | content.
- `theme.py`: Material Design 3 ColorTokens（primary 0-900, surface tones, semantic tokens）

### backup/ — Backup Engine (Pluggable)
- `engine.py`: `BackupEngine` ABC. Methods: `create_plan`, `update_plan`, `delete_plan`, `enable`, `disable`, `query_status`, `probe`.
- `windows_task.py`: Adapter wrapping `services/backup_service.py`. Uses `schtasks.exe`.
- `maintenance_plan.py`: SQL Agent via `sp_add_job`/`sp_add_jobstep`/`sp_add_schedule`. Compatible SQL 2008–2022.
- `factory.py`: `get_engine(id)`, `list_engines()`, `probe_engines(instance)`.

### core/ — Business Logic
- `project_manager.py`: `ProjectManager` (static class). CRUD for projects + clients.
- `wg_keygen.py`: Python X25519 key generation (cryptography), wg.exe fallback for `wg show`.
- `templates.py`: WireGuard `.conf` string templates.
- `qrcode_gen.py`: QR code from client config (qrcode[pil] or SVG fallback).

### models/ — Data
- `Project` wraps `ProjectSettings` (name, public_ip, vpn_ip, etc.), `KeyPair` (server keys), `List[ClientEntry]`.
- `BackupPolicy`: enabled, databases[], schedule_time, save_path, retention_days, compression.
- Serialization: `to_dict()` / `from_dict()` — project.json is the only source of truth.

### pages/ — UI Pages
Each page is a `CTkFrame` subclass constructed via `app._switch_to(PageClass, self, *args)`.

| Page | File | Mode | Key Sections |
|------|------|------|-------------|
| Server Dashboard | `server_dashboard_page.py` | SERVER | CPU/内存/磁盘 + 服务状态 |
| Client Dashboard | `client_dashboard_page.py` | CLIENT | 项目/客户统计 |
| Projects | `projects_page.py` | CLIENT | 项目列表/新建/打开 |
| Customers | `customers_page.py` | CLIENT | 客户列表 + 新建（含远程信息 + 可选 WG） |
| WireGuard | `wireguard_server_page.py` | SERVER | 安装状态/打开官方客户端 |
| WireGuard Config | `wireguard_client_page.py` | CLIENT | 配置生成/客户端CRUD/部署包 |
| SQL Server | `sql_page.py` | SERVER | Port / Listen mode / Restart |
| Firewall | `firewall_page.py` | SERVER | Service toggles + Custom port |
| Backup Center | `backup_page.py` | SERVER | Quick Mode / History / Restore / Browser |
| System Info | `system_info_page.py` | SERVER | 系统信息 / 服务管理 |
| Ops Info | `ops_page.py` | CLIENT | Editable ops form |
| Settings | `settings_page.py` | BOTH | Workspace mode / Theme / About |

### services/ — Backend Services
- `backup_service.py`: Immediate backup, history, file browser, health, cleanup, SQL Agent job list.
- `sql_service.py`: SQL Server registry + SCM (reg.exe/sc.exe → sqlcmd SHUTDOWN).
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
