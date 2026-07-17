# GP Server Manager — AGENTS.md

## Project

**GP Server Manager（服务器管理器）** — 管家婆代理商/企业 IT 运维工具。
管理服务器，而不是生成配置文件。Project = 一台服务器。

原 WireGuard Config Generator，已重构为企业级 Server Lifecycle Manager。

## 核心文件

| 模块 | 文件 | 职责 |
|------|------|------|
| **app/** | `app.py` | GPServerManager 主窗口（侧边栏 + 页面路由 + toast/modal） |
| | `workspace.py` | WorkspaceMode(SERVER/CLIENT/BOTH) + nav items per mode + section分组 |
| | `launcher.py` | 启动模式选择对话框（Lucide icon + 左侧指示条选中态） |
| | `theme.py` | 设计 token（C/PAD/CR 常量），浅色模式 |
| **backup/** | `engine.py` | BackupEngine ABC（所有备份引擎的接口） |
| | `windows_task.py` | Windows Task Scheduler 引擎 |
| | `maintenance_plan.py` | SQL Server Agent Job 引擎 |
| | `factory.py` | 引擎工厂 + 检测 |
| **core/** | `project_manager.py` | ProjectManager — 所有业务逻辑 |
| | `wg_keygen.py` | Python X25519 密钥生成（cryptography），wg.exe 降级回退 |
| | `templates.py` | WireGuard 配置模板 |
| | `qrcode_gen.py` | 二维码生成 |
| **models/** | `project.py` | Project / ProjectSettings / OpsInfo / SqlConfig / RemoteInfo |
| | `app_settings.py` | AppSettings — 持久化 settings.json（workspace）|
| | `workspace.py` | WorkspaceMode 枚举（无 GUI 依赖，防循环导入） |
| | `client.py` | ClientEntry + ClientStatus（含 remote_type/id/password） |
| | `keypair.py` | KeyPair dataclass |
| | `backup.py` | BackupPolicy |
| **pages/** | `server_dashboard_page.py` | Server 仪表盘（4 药丸 + 状态条） |
| | `client_dashboard_page.py` | Client 仪表盘（项目概览 + 运维信息 inline 编辑） |
| | `projects_page.py` | 项目列表（Lucide 图标 + EmptyState） |
| | `customers_page.py` | 客户管理（新建/编辑/复制远程信息） |
| | `wireguard_server_page.py` | WireGuard 状态 + 打开官方客户端（Server Mode） |
| | `wireguard_client_page.py` | WireGuard 配置生成 + 客户端 CRUD（Client Mode） |
| | `backup_page.py` | 备份中心（CTkTabview: 极速备份/历史/恢复/文件） |
| | `sql_page.py` | SQL Server 配置 |
| | `firewall_page.py` | 防火墙管理 |
| | `system_info_page.py` | 系统信息 + 服务管理（已合并，无 radio tab 切换） |
| | `ops_page.py` | 运维信息编辑（已合并进 dashboard，保留向后兼容） |
| | `settings_page.py` | 全局设置（工作模式切换，浅色主题标记） |
| **services/** | `backup_service.py` | 立即备份/历史/清理/恢复/文件浏览 |
| | `sql_service.py` | SQL Server 注册表/服务（支持 SQL 2008~2022） |
| | `firewall_service.py` | netsh advfirewall 封装 |
| | `system_service.py` | 系统信息（CPU/内存/磁盘/网络） |
| | `wireguard_service.py` | wg show 解析/状态检测 |
| **utils/** | `file_ops.py` | ensure_dir / write_json / read_json / open_folder |
| | `icon_loader.py` | Lucide SVG → PIL → CTkImage 运行时渲染（19 icon） |
| **widgets/** | `__init__.py` | 可复用组件（SidebarButton/CardFrame（带边框）/StatusIndicator） |
| | `toast.py` | ToastFrame（浮动通知）+ ModalConfirm（危险操作确认） |
| | `empty_state.py` | EmptyState（Lucide icon + 文字 + CTA 按钮） |
| **main.py** | | 入口 |

## Architecture

### Workspace 模式

```
启动 → WorkspaceLauncher → Server Mode / Client Mode
  Server Mode: 服务器本机操作（SQL/WireGuard/防火墙/备份/系统信息）
  Client Mode: 运维电脑操作（项目/客户/WireGuard配置）
  
项目依赖项（客户/WireGuard）在有项目打开时才在侧边栏显示
设置始终可见
```

### 模块分层

```
main.py
  └─ app/          ← 主窗口 + 侧边栏导航
       ├─ backup/  ← 可插拔备份引擎（ABC → WindowsTask / MaintenancePlan）
       ├─ core/    ← 业务逻辑（project_manager → 密钥生成 → 模板）
       ├─ models/  ← 数据模型（dataclass + JSON 序列化）
       ├─ pages/   ← 页面（每个 page 是 CTkFrame 子类）
       ├─ services/ ← 后端服务（SQL/防火墙/WireGuard/系统）
       ├─ utils/   ← 文件 I/O + 图标引擎
       └─ widgets/ ← 可复用 UI 组件（toast/empty state/card）
```

- **全类型注解 + dataclass + pathlib**
- **MVC/MVVM**：GUI（pages/）只做交互，不包含业务逻辑
- **所有操作通过 ProjectManager 静态方法或 BackupEngine 接口**
- **设计 token**：C dict（颜色）/ PAD（间距）/ CR（圆角），所有页面统一引用

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
- **SQL 服务操作** — reg.exe/sc.exe 为主，sqlcmd SHUTDOWN 重启
- **页面切换** — `_switch_to` destroy 旧页 → `after(60)` → `_do_render`（60ms 呼吸延迟）
- **Toast 分两类** — 危险操作（删除/恢复）用 modal 弹窗，非危险消息用 toast 浮动通知
- **卡片 1px 边框** — CardFrame 默认 `border_width=1, border_color=#CAC4D0`
- **Lucide 图标** — 通过 `utils/icon_loader.py` 运行时 SVG→PNG 渲染，零 native 依赖

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

## 环境依赖

- `wg.exe`（WireGuard，仅 WireGuard 状态页面需要，可选）
- `customtkinter`（GUI）
- `qrcode[pil]`（二维码，可选）
- `psutil`（系统信息）
- `svg.path`（Lucide SVG 路径解析，纯 Python）
