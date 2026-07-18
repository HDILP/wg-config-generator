"""WireGuard config file templates — all text templates in one place."""
from __future__ import annotations

SERVER_CONF = """[Interface]
PrivateKey = {private_key}
Address = {address}
ListenPort = {listen_port}
{peers_section}"""

PEER_BLOCK = """[Peer]
# {client_name}
PublicKey = {public_key}
AllowedIPs = {allowed_ips}"""

CLIENT_CONF = """[Interface]
PrivateKey = {private_key}
Address = {address}
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {allowed_ips}
PersistentKeepalive = {persistent_keepalive}"""

README = """GP Server Manager — WireGuard Configuration
==============================================

Server: {server_name}
Public IP: {server_public_ip}
Server VPN: {server_vpn_ip}
Client VPN: {client_vpn_ip}
Listen Port: {listen_port}

Deployment:
  1. Import server.conf on the server
  2. Import client.conf on the client
  3. Activate
  4. Verify with `wg show`

Remote Access: {remote_type} / {remote_id}
Contact: {contact}
"""

CLIENT_README = """{client_name}
{vpn_ip}
Server: {server_public_ip}:{listen_port}

1. Install WireGuard
2. Import client.conf
3. Activate
"""
