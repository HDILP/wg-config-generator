# WireGuard Config Generator

一键生成 WireGuard 配置。支持**新建服务器**和**为已有服务器新增客户端**两种模式。

## Requirements

- Python 3.10+
- [WireGuard](https://www.wireguard.com/install/)（`wg` 需在 PATH 或默认安装路径）
- `pip install -r requirements.txt`

## Usage

```bash
python main.py
```

### New Server 模式
1. 填写 Server Public IP
2. 点击 Generate
3. 所有配置自动写入 output/ 目录

### Add Client 模式
1. 切换到 "Add Client"
2. 选择已有 server.conf 所在目录
3. Client VPN IP 自动检测下一个可用地址
4. 点击 Generate — 自动追加 [Peer] 并生成新的 client_xxx.conf

## Output

```
output/
├── server.conf           # 服务端配置
├── client.conf           # 首个客户端
├── client_002.conf       # 追加的客户端
├── client_002_public.txt
├── README.txt
├── server_public.txt
└── keys.json             # 服务器 + 所有客户端密钥（JSON）
```

## keys.json 格式

```json
{
  "server": { "private": "...", "public": "..." },
  "peers": [
    { "name": "client_001", "private": "...", "public": "...", "ip": "10.66.66.2" },
    { "name": "client_002", "private": "...", "public": "...", "ip": "10.66.66.3" }
  ]
}
```

## Architecture

```text
Server
├── client_001  (client.conf)
├── client_002  (client_002.conf)
└── client_003  (client_003.conf)
```

## CI

push 后 GitHub Actions 自动用 Nuitka 编译 Windows 单文件 exe，artifact 可下载。

## 扩展方向（需时再说）
- 客户端二维码
- 一键吊销 [Peer]
- 导入已有 server.conf 补全 keys.json
