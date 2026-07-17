# GP Server Manager

> 企业级 Windows 服务器生命周期管理工具。
> 面向管家婆代理商和企业 IT 售后，管理服务器而不是生成配置文件。

原生 Windows exe（Nuitka 编译），不依赖 Python 环境。

---

## Features

### 服务器项目管理
- **Project = 一台服务器** — 所有配置集中在一个目录，不散落
- **Workspace 工作模式** — Server Mode（服务器本机操作）和 Client Mode（运维电脑操作）
| **Client Dashboard** — 项目统计、最近项目列表、运维信息 inline 编辑

### WireGuard
- **Client Mode** — 配置生成、客户端 CRUD、VPN IP 自动分配、部署包生成
- **Server Mode** — 仅显示安装状态 + 打开官方 WireGuard 客户端
- **二维码导出** — client.conf 一键转二维码
- **Win7 支持** — 部署包使用 TunSafe，附带 TunSafe-TAP 和 TunSafe 主程序，无需额外安装系统补丁

### 备份中心（Backup Center）
- **双引擎架构** — Windows 计划任务 / SQL Server Agent Job 可切换
- **极速模式** — 一键启用，无需理解 SQL Agent、Maintenance Plan 等概念
- **数据库多选** — 自动读取 `sys.databases`，过滤系统库
- **立即备份** — 多库串行 + 实时进度 + 逐库结果
- **定时备份** — 支持压缩、保留策略（自动清理过期 .bak）
- **恢复** — 简化界面，选备份文件 → 原库/新库 → 覆盖选项
- **备份浏览器** — 按日期分组显示 .bak 文件
- **健康仪表** — 上次成功 / 失败 / 剩余磁盘

### WireGuard
- **服务器管理** — 密钥生成、配置导出
- **客户端 CRUD** — 新增/删除/重新生成密钥
- **自动 IP 分配** — 扫描 used IPs 取第一个空闲地址
- **二维码导出** — client.conf 一键转二维码
- **不得重新生成服务器密钥**

### SQL Server
- 查看 SQL 版本、状态、端口、TCP/IP 状态、监听方式
- 修改端口、切换监听（本机/全部地址）
- 重启 SQL 服务
- **封装 IPAll/IP1/IP2/TcpDynamicPorts** — GUI 不暴露注册表概念

### Windows 防火墙
- 常用服务开关（SQL/RDP/SMB/HTTP/HTTPS）
- 自定义端口
- **不需要用户输入 netsh 命令**

|### 运维信息
- 远程软件（帮我吧/向日葵/ToDesk/RustDesk）
- 负责人、密码、备注、区域、SQL 版本、管家婆版本
- **已合并到 Client Dashboard，无需单独页面**

### 工具箱
- Ping、Traceroute、公网 IP 检测
- WireGuard 重启、服务重启

---

## Requirements

- **Windows 7+**（编译产物）或 **Python 3.8+**（源码运行）
- WireGuard 状态页面需要 [WireGuard](https://www.wireguard.com/install/)（可选，密钥生成无依赖）
- 备份引擎需要 SQL Server（Maintenance Plan 引擎需要 SQL Agent 运行中）
- `pip install -r requirements.txt`（源码运行）

---

## Usage

```bash
# 源码运行
python main.py
```

启动后选择工作模式：

- **Server Mode** — 在服务器上运行，管理 SQL/WireGuard/防火墙/备份/系统
- **Client Mode** — 在运维电脑上运行，管理项目/客户/配置生成/部署包

### 新建服务器（Client Mode）
1. 启动 Client Mode → 点击 **新建项目**
2. 填写项目名称、公网 IP、远程信息等
3. 点击创建 → 自动生成密钥
4. 在仪表盘查看项目详情

### 配置自动备份（Server Mode）
1. 启动 Server Mode → 侧边栏 **自动备份**
2. 选择备份方式（Windows 计划任务 / SQL Server 计划）
3. 勾选数据库、设置时间/路径/保留天数
4. 点击 **一键启用** 或 **创建**

### 生成部署包（Client Mode）
1. 打开项目 → 侧边栏 **WireGuard 配置**
2. 添加客户端
3. 点击 **生成部署包**
4. 选择目标（服务器/客户端）和目标系统（Win10+/Win7）
5. 生成 ZIP，复制到目标机安装

---

## Architecture

```
启动 → WorkspaceLauncher → Server Mode / Client Mode

main.py
  └─ app/          ← GPServerManager + workspace 选择 + 页面路由
       ├─ backup/  ← 可插拔备份引擎（ABC 接口）
       │    ├─ engine.py            ← BackupEngine 抽象基类
       │    ├─ windows_task.py      ← Windows Task Scheduler
       │    ├─ maintenance_plan.py  ← SQL Agent Job（sp_add_job）
       │    └─ factory.py           ← 引擎工厂 + 检测
       ├─ core/    ← 业务逻辑
       ├─ models/  ← 数据模型（dataclass + JSON 序列化）
       ├─ pages/   ← UI 页面（CTkFrame 子类）
       ├─ services/ ← 后端服务
       ├─ utils/   ← 文件 I/O
       └─ widgets/ ← 可复用 UI 组件
```

### Backup Engine 架构

用户选择引擎 → Factory → `get_engine(id)` → 多态调用 create/update/delete/status

- Windows 计划任务：调用 schtasks.exe
- SQL Server 计划：调用 sp_add_job / sp_update_jobstep / sp_delete_job（兼容 SQL 2008–2022）

---

## Project Layout

```
Projects/
├── 深圳一区/
│   ├── project.json              # 唯一数据源
│   ├── server.conf               # 自动生成
│   ├── server_public.txt
│   ├── README.txt
│   ├── backup_history.json       # 备份记录
│   ├── scripts/
│   │   └── auto_backup.ps1       # Windows Task 脚本
│   └── clients/
│       └── 深圳华润/
│           ├── client.conf
│           ├── README.txt
│           ├── keys.json
│           └── qrcode.png
└── 广州二区/
    └── ...
```

---

## 项目结构（开发）

```
wg-config-generator/
├── main.py                   # 入口
├── app/
│   ├── app.py                # 主窗口
│   └── theme.py              # 主题
├── backup/                   # 备份引擎
├── core/                     # 业务逻辑
├── models/                   # 数据模型
├── pages/                    # UI 页面（12 个）
├── services/                 # 后端服务（5 个）
├── utils/                    # 工具函数 + 图标引擎
├── widgets/                  # 可复用组件（toast/empty state/card）
├── requirements.txt
├── AGENTS.md
├── README.md
└── .github/workflows/build.yml
```

44 个 Python 源文件，全类型注解，无巨大 main.py。

---

## CI

`.github/workflows/build.yml`

- push 自动触发
- Nuitka 编译为 Windows 单文件 exe
- Python 3.8（Win7 兼容）
- artifact: `gp-server-manager-win` → `GPServerManager.exe`

---

## 开发

```bash
git clone https://github.com/HDILP/wg-config-generator
cd wg-config-generator
pip install -r requirements.txt
python main.py
```

### 分支

- `feat/gp-server-manager` — 当前开发分支（模块化重构）
- `main` — 原 WireGuard Config Generator（旧版）

---

## 设计理念

> 本项目不是"WireGuard 配置生成器"，而是**服务器生命周期管理工具（Server Lifecycle Manager）**。

所有功能围绕三个核心场景：
1. **交付一台新服务器**
2. **维护一台运行中的服务器**
3. **管理多台服务器**

让不会网络知识的售后人员也能完成标准化部署。
