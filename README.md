# WireGuard Project Manager

管家婆代理商专用 — 多服务器项目管理工具。

## Usage

```bash
python main.py
```

### Home

- **新建服务器** — 创建新 WireGuard 项目（生成 server keypair + 首个 client）
- **打开已有服务器** — 选择已有项目，管理客户

### Project Detail

每个项目独立管理：

```
projects/<服务器名称>/
├── project.json      # 唯一数据源
├── server.conf       # 自动生成
├── server_public.txt
├── README.txt
└── clients/
    ├── 深圳华润万家/
    │   └── client.conf   # 可直接发给客户导入
    └── 东莞XX商场/
        └── client.conf
```

- 新增客户 → 自动分配 IP，生成密钥，追加 [Peer]
- 删除客户 → 移除 [Peer]，清理文件
- `project.json` 是唯一数据源，所有 `.conf` 均由程序重新生成

## Requirements

- Python 3.10+
- [WireGuard](https://www.wireguard.com/install/)（`wg` 需在 PATH 或默认安装路径）
- `pip install -r requirements.txt`

## CI

push 后 GitHub Actions 自动用 Nuitka 编译 Windows 单文件 exe。
