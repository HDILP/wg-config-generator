"""Windows Firewall service — manage firewall rules via netsh advfirewall.

All Windows-only; returns dummy data on other platforms.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FirewallRule:
    name: str
    enabled: bool = True
    direction: str = "IN"
    protocol: str = "TCP"
    local_port: str = ""
    remote_ip: str = "Any"
    action: str = "Allow"


def _netsh(args: str) -> str:
    import subprocess
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall"] + args.split(),
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return f"<error: {exc}>"


# ── well-known rules ────────────────────────────────────────────
# ponytail: fixed mapping, extend by adding to dict
WELL_KNOWN_PORTS: Dict[str, int] = {
    "SQL": 1433,
    "RDP": 3389,
    "SMB": 445,
    "HTTP": 80,
    "HTTPS": 443,
    "WINRM": 5985,
    "WINRM_HTTPS": 5986,
}


def is_rule_enabled(name_substring: str) -> bool:
    """Check if any rule matching the substring is enabled."""
    if sys.platform != "win32":
        return True  # assume OK on dev
    rules = list_rules()
    for r in rules:
        if name_substring.lower() in r.name.lower():
            return r.enabled
    return False


def list_rules() -> List[FirewallRule]:
    """List all inbound firewall rules (returns limited set on non-Windows)."""
    if sys.platform != "win32":
        return [
            FirewallRule(name="SQL (dev mock)", enabled=True, local_port="65529"),
            FirewallRule(name="RDP (dev mock)", enabled=True, local_port="3389"),
            FirewallRule(name="SMB (dev mock)", enabled=False, local_port="445"),
        ]

    raw = _netsh("show rule name=all dir=in")
    rules: List[FirewallRule] = []
    current: Optional[FirewallRule] = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("Rule Name:"):
            if current:
                rules.append(current)
            current = FirewallRule(name=line.split(":", 1)[1].strip())
        elif current:
            if line.startswith("Enabled:"):
                current.enabled = "Yes" in line
            elif line.startswith("Direction:"):
                current.direction = line.split(":", 1)[1].strip()
            elif line.startswith("Protocol:"):
                current.protocol = line.split(":", 1)[1].strip()
            elif line.startswith("LocalPort:"):
                current.local_port = line.split(":", 1)[1].strip()
            elif line.startswith("RemoteIP:"):
                current.remote_ip = line.split(":", 1)[1].strip()
            elif line.startswith("Action:"):
                current.action = line.split(":", 1)[1].strip()
    if current:
        rules.append(current)
    return rules


def add_rule(
    name: str,
    port: int,
    protocol: str = "TCP",
    action: str = "Allow",
) -> str:
    """Add a firewall rule to allow a port."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"

    return _netsh(
        f'add rule name="{name}" dir=in protocol={protocol} '
        f"localport={port} action={action}"
    )


def remove_rule(name: str) -> str:
    """Remove a firewall rule by name."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    return _netsh(f'delete rule name="{name}" dir=in')


def enable_rule(name: str) -> str:
    """Enable a firewall rule."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    # netsh doesn't have enable/disable directly; we use the rule name
    return _netsh(f"set rule name=\"{name}\" new enable=Yes")


def disable_rule(name: str) -> str:
    """Disable a firewall rule."""
    if sys.platform != "win32":
        return "n/a (non-Windows)"
    return _netsh(f"set rule name=\"{name}\" new enable=No")


def apply_well_known(name: str, enabled: bool) -> str:
    """Toggle a well-known service rule."""
    port = WELL_KNOWN_PORTS.get(name)
    if not port:
        return f"Unknown service: {name}"

    rule_name = f"GP Server Manager - {name} ({port})"
    if enabled:
        return add_rule(rule_name, port)
    else:
        return remove_rule(rule_name)


def apply_custom_port(port: int, protocol: str = "TCP") -> str:
    """Add a custom port rule named after the port."""
    rule_name = f"GP Server Manager - Custom {protocol}:{port}"
    return add_rule(rule_name, port, protocol)
