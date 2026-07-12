# WireGuard Project Manager — CLAUDE.md

## Project

管家婆代理商专用 WireGuard 配置管理工具。多项目管理，project.json 为唯一数据源。

## 核心文件

| 文件 | 职责 |
|------|------|
| `gui.py` | CustomTkinter 多页面 GUI |
| `generator.py` | `ProjectManager` — 所有业务逻辑（create / add_client / remove_client / save） |
| `models.py` | `Project` / `ClientEntry` / `KeyPair` dataclass |
| `keygen.py` | `wg.exe` 封装（genkey / pubkey / derive_pubkey / find_wg） |
| `templates.py` | WireGuard 配置模板（字符串常量） |
| `utils.py` | 文件 I/O / open_folder |
| `wireguard-installer.exe` | 捆绑的 WireGuard 安装程序（86KB） |

## Architecture

- `ProjectManager` 是**无状态静态类** — 所有方法都是 `@staticmethod`
- GUI 只做交互，不包含业务逻辑
- `_write_project(project)` 写入 project.json + 重新生成所有 .conf 文件
- `_write_configs(project)` 重新生成 server.conf + 所有 client.conf

## 数据流

```
GUI 操作 → ProjectManager.xxx() → _write_project() → write_json(project.json) → _write_configs()
```

## 关键约定

- **不改 project.json 外的 .conf 文件** — 全部由程序重新生成
- **客户端 IP 自动分配** — 扫描 used IPs 取第一个空闲 .2–.254
- **wg.exe 检测** — 先查 `C:\Program Files\WireGuard\wg.exe` / `C:\Program Files (x86)\WireGuard\wg.exe`，再兜底 PATH
- **GUI 用 threading** — 所有耗时操作后台线程，避免卡 UI
- **项目名唯一** — `(ProjectManager.PROJECTS_DIR / name).exists()` 拦截重复

## 磁盘布局

```
projects/<name>/
├── project.json          # 唯一数据源
├── server.conf           # 自动生成
├── server_public.txt
├── README.txt
└── clients/<name>/
    └── client.conf
```

## CI

`.github/workflows/build.yml` — Nuitka onefile 编译 Windows exe（含捆绑的 wireguard-installer.exe）

## 环境依赖

- `wg.exe`（WireGuard）
- `customtkinter`（GUI）
