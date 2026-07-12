# GP Server Manager — CLAUDE.md

## Project

**GP Server Manager（服务器管理器）** — 管家婆代理商/企业 IT 运维工具。
管理服务器，而不是生成配置文件。Project = 一台服务器。

原 WireGuard Config Generator，已重构为企业级 Server Lifecycle Manager。

## 核心文件

| 模块 | 文件 | 职责 |
|------|------|------|
| **app/** | `app.py` | GPServerManager 主窗口（侧边栏 + 页面路由） |
| | `theme.py` | Material You 主题（浅色/深色/系统） |
| **backup/** | `engine.py` | BackupEngine ABC（所有备份引擎的接口） |
| | `windows_task.py` | Windows Task Scheduler 引擎 |
| | `maintenance_plan.py` | SQL Server Agent Job 引擎 |
| | `factory.py` | 引擎工厂 + 检测 |
| **core/** | `project_manager.py` | ProjectManager — 所有业务逻辑 |
| | `wg_keygen.py` | wg.exe 封装（genkey/pubkey/find_wg） |
| | `templates.py` | WireGuard 配置模板 |
| | `qrcode_gen.py` | 二维码生成 |
| **models/** | `project.py` | Project / ProjectSettings / OpsInfo / SqlConfig / RemoteInfo |
| | `client.py` | ClientEntry + ClientStatus |
| | `keypair.py` | KeyPair dataclass |
| | `backup.py` | BackupPolicy |
| **pages/** | `home_page.py` | 首页（新建/打开/最近项目） |
| | `dashboard_page.py` | 仪表盘（状态 + 安全评分） |
| | `backup_page.py` | 备份中心（极速/历史/恢复/浏览器） |
| | `wireguard_page.py` | WireGuard 管理 |
| | `sql_page.py` | SQL Server 配置 |
| | `firewall_page.py` | 防火墙管理 |
| | `ops_page.py` | 运维信息编辑 |
| | `tools_page.py` | 工具箱（Ping/Traceroute/公网IP/服务重启） |
| | `settings_page.py` | 全局设置 |
| **services/** | `backup_service.py` | 立即备份/历史/清理/恢复/文件浏览 |
| | `sql_service.py` | SQL Server 注册表/服务（PowerShell + cmd 双路径） |
| | `firewall_service.py` | netsh advfirewall 封装 |
| | `system_service.py` | Ping/Traceroute/公网IP/系统信息 |
| | `wireguard_service.py` | wg show 解析/状态检测 |
| **utils/** | `file_ops.py` | ensure_dir / write_json / read_json / open_folder |
| **widgets/** | `__init__.py` | 可复用组件（SidebarButton/StatusIndicator/SecurityScore/Card） |
| **main.py** | | 入口 |

## Architecture

### 模块分层

```
main.py
  └─ app/          ← 主窗口 + 侧边栏导航
       ├─ backup/  ← 可插拔备份引擎（ABC → WindowsTask / MaintenancePlan）
       ├─ core/    ← 业务逻辑（project_manager → 密钥生成 → 模板）
       ├─ models/  ← 数据模型（dataclass + JSON 序列化）
       ├─ pages/   ← 页面（每个 page 是 CTkFrame 子类）
       ├─ services/ ← 后端服务（SQL/防火墙/WireGuard/系统）
       ├─ utils/   ← 文件 I/O
       └─ widgets/ ← 可复用 UI 组件
```

- **全类型注解 + dataclass + pathlib**
- **MVC/MVVM**：GUI（pages/）只做交互，不包含业务逻辑
- **所有操作通过 ProjectManager 静态方法或 BackupEngine 接口**

### Backup Engine 架构

```
BackupEngine (ABC)
  ├─ WindowsTaskEngine      ← 适配器，调用 services/backup_service.py
  └─ MaintenancePlanEngine  ← SQL Agent (sp_add_job) 实现
        ↓ Factory
  UI  → get_engine(id) → 多态调用
```

### 数据流（WireGuard）

```
GUI 操作 → ProjectManager.xxx() → _write_project() → write_json(project.json) → _write_configs()
```

## 关键约定

- **零阉割原则** — 新版必须保留旧版全部功能，只增不减。删除旧功能一律需确认。
- **project.json 唯一数据源** — 所有 .conf 均由程序重新生成，人工修改会覆盖
- **客户端 IP 自动分配** — 扫描 used IPs 取第一个空闲 .2–.254
- **wg.exe 检测** — 先查 `C:\Program Files\WireGuard\wg.exe`，再 PATH
- **GUI 用 threading** — 所有耗时操作后台线程，避免卡 UI
- **项目名唯一** — `(ProjectManager.PROJECTS_DIR / name).exists()` 拦截重复
- **Windows Task 和 Maintenance Plan 互不影响** — 切换引擎不会自动删除另一方
- **SQL 服务双路径** — 有 PowerShell 走 ps，没有就 `reg.exe` + `sc.exe`（Win7）
- **所有页面构造** — `_switch_to(page_class, self, ...args)`，page 在 destroy 后才创建

## 磁盘布局

```
Projects/<name>/
├── project.json            # 唯一数据源（含 backup policy / sql / ops 等）
├── server.conf             # 自动生成
├── server_public.txt
├── README.txt
├── backup_history.json     # 备份历史（自动维护）
├── scripts/
│   └── auto_backup.ps1     # Windows Task 用（自动生成）
└── clients/<name>/
    ├── client.conf
    ├── README.txt
    ├── keys.json
    └── qrcode.png
```

### project.json 结构

```json
{
  "name": "深圳一区",
  "public_ip": "117.xxx.xxx.xxx",
  "listen_port": 51820,
  "vpn_ip": "10.66.66.1",
  "subnet": "10.66.66.0/24",
  "remote": { "type": "帮我吧", "id": "" },
  "sql": { "instance": "MSSQLSERVER", "port": 65529, "listen": "127.0.0.1" },
  "ops": { "remote_type": "", "contact": "", "password": "", ... },
  "backup": { "enabled": false, "databases": [], "schedule_time": "02:00", ... },
  "note": "",
  "clients": [...]
}
```

## CI

`.github/workflows/build.yml` — Nuitka onefile
- Python 3.8（Win7 兼容）
- `--include-package=app,backup,core,models,pages,services,utils,widgets`
- 输出: `GPServerManager.exe`
- artifact: `gp-server-manager-win`

## 环境依赖

- `wg.exe`（WireGuard，仅 WireGuard 页面需要）
- `customtkinter`（GUI）
- `qrcode[pil]`（二维码，可选）
- `psutil`（系统信息）
