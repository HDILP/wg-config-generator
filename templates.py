"""WireGuard config file templates — all strings in one place."""

SERVER_CONF = """[Interface]
PrivateKey = {private_key}
Address = {address}
ListenPort = {listen_port}

{peers_section}"""

PEER_BLOCK = """[Peer]
PublicKey = {public_key}
AllowedIPs = {allowed_ips}"""

CLIENT_CONF = """[Interface]
PrivateKey = {private_key}
Address = {address}

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {allowed_ips}
PersistentKeepalive = {persistent_keepalive}"""

README = """WireGuard Configuration

Server Public IP:
{server_public_ip}

Server VPN:
{server_vpn_ip}

Client VPN:
{client_vpn_ip}

Listen Port:
{listen_port}

Deployment:

1.
Import server.conf

2.
Import client.conf

3.
Activate

Done."""
