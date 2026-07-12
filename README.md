# WireGuard Project Manager

管家婆代理商专用 — 多服务器项目管理工具。

原生 Windows exe（含一键安装 WireGuard），不依赖 Python 环境。

## Features

- **多项目独立管理** — 每个 WireGuard 服务器是一个独立项目
- **新建服务器** — 一键生成 server keypair + 首个 client
- **新增客户端** — 自动分配 VPN IP，生成密钥，追加 [Peer]，不重新生成服务器密钥
- **删除客户端** — 一键移除 [Peer]，清理文件，不覆盖 server.conf
- **远程协助号码** — 每台服务器可记录帮我吧 / 向日葵号码，随时修改
- **一键安装 WireGuard** — 安装程序内置在 exe 中，检测到缺失时自动提示安装
- **project.json 为唯一数据源** — 所有 `.conf` 文件均由程序重新生成

## Requirements

- **Windows 7+**（编译产物）或 **Python 3.10+**（源码运行）
- [WireGuard](https://www.wireguard.com/install/)（`wg` 需在 `C:\Program Files\WireGuard\` 或 PATH 中）
- `pip install -r requirements.txt`（源码运行）

## Usage

```bash
# 源码运行
python main.py

# 或直接运行 CI 编译的 WireGuardConfigGenerator.exe
```

### 新建服务器

1. Home → **新建服务器**
2. 填写服务器名称、公网 IP、端口等
3. 点击 Create → 自动生成 server keypair + 第一个 client
4. 进入项目详情页

### 新增客户端

1. 打开已有服务器项目
2. 点击 **新增客户**
3. 输入客户名称，VPN IP 自动分配下一个可用地址
4. 程序自动：生成 keypair → 追加 server.conf [Peer] → 生成 client.conf

### 删除客户端

1. 客户行点击 **✕**
2. 确认 → 自动移除 [Peer] + 删除 client 目录

## Project Layout

```
projects/
├── 管家婆云服务器01/
│   ├── project.json          # 唯一数据源（服务器密钥 + 客户列表 + 元数据）
│   ├── server.conf           # 由程序自动生成
│   ├── server_public.txt
│   ├── README.txt
│   └── clients/
│       ├── 深圳华润万家/
│       │   └── client.conf   # 可直接发给客户导入 WireGuard
│       └── 东莞XX商场/
│           └── client.conf
└── 管家婆云服务器02/
    └── ...
```

### project.json

```json
{
  "name": "管家婆云服务器01",
  "remote_number": "123 456 789",
  "server": {
    "public_ip": "117.xxx.xxx.xxx",
    "private_key": "...",
    "public_key": "...",
    "vpn_ip": "10.66.66.1",
    "listen_port": 51820
  },
  "vpn_subnet": "10.66.66.0/24",
  "clients": [
    {
      "name": "深圳华润万家",
      "vpn_ip": "10.66.66.2",
      "private_key": "...",
      "public_key": "..."
    }
  ]
}
```

## Architecture

```
gui.py          →  多页面 GUI（Home → 新建 / 项目详情 → 客户管理）
generator.py    →  ProjectManager（create / add_client / remove_client / save / regenerate）
models.py       →  Project / ClientEntry / KeyPair（dataclass + JSON 序列化）
keygen.py       →  wg.exe 封装（genkey / pubkey / find_wg）
templates.py    →  WireGuard 配置模板
utils.py        →  文件 I/O / open_folder
main.py         →  入口
```

所有关键操作都在 `generator.ProjectManager` 中，GUI 层只做用户交互。

## CI

`.github/workflows/build.yml`

- push 自动触发
- Nuitka 编译为 Windows 单文件 exe
- 内置 `wireguard-installer.exe`
- artifact: `wg-config-generator-win`

## 开发

```bash
git clone https://github.com/HDILP/wg-config-generator
cd wg-config-generator
pip install customtkinter
python main.py
```
