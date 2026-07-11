# WireGuard Config Generator

一键生成 WireGuard 服务端 + 客户端配置。

## Requirements

- Python 3.10+
- [WireGuard](https://www.wireguard.com/install/) （`wg` 需在 PATH 中）
- `pip install -r requirements.txt`

## Usage

```bash
python main.py
```

1. 填写 Server Public IP
2. 点击 Generate
3. 所有配置自动写入 output/ 目录

## Output

```
output/
├── server.conf        # 服务端配置（含 [Peer]）
├── client.conf        # 客户端配置
├── README.txt         # 部署说明
├── server_public.txt  # 服务端公钥（文本）
├── client_public.txt  # 客户端公钥（文本）
└── keys.json          # 完整密钥备份
```

## Architecture

当前默认生成 1 个 Server + 1 个 Client。

代码结构已预留多客户端扩展：

```
Server
├── Client001
├── Client002
└── Client003
```

无需重构，在 `ServerConfig.peers` 列表追加 `PeerConfig` 即可。

## 扩展方向

- [ ] 多客户端批量生成
- [ ] 客户端二维码（qrcode）
- [ ] 导入已有 server.conf 追加 [Peer]
- [ ] 一键吊销客户端
- [ ] Nuitka 打包为单文件 exe
