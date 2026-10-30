"""Fail-closed IPv4/IPv6 CIDR checks for trusted LAN clients.

Use only with a client address obtained from a trusted reverse proxy or the
network edge. Never pass an arbitrary client-supplied forwarding header here.
The reverse proxy/firewall remains the primary enforcement point.
"""
from __future__ import annotations

import ipaddress
from collections.abc import Iterable


def parse_trusted_networks(values: Iterable[str]):
    networks = []
    for value in values:
        value = str(value).strip()
        if not value or value.startswith("#"):
            continue
        networks.append(ipaddress.ip_network(value, strict=False))
    return tuple(networks)


def is_trusted_client(client_ip: str | None, trusted_cidrs: Iterable[str]) -> bool:
    """Return False for missing/malformed client IP or an empty allowlist."""
    if not client_ip:
        return False
    try:
        address = ipaddress.ip_address(str(client_ip).strip())
        networks = parse_trusted_networks(trusted_cidrs)
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in networks)


def detected_private_addresses() -> list[str]:
    """Return private IPv4 addresses discoverable from the host name."""
    import socket

    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = ipaddress.ip_address(info[4][0])
            if address.is_private and not address.is_loopback and not address.is_link_local:
                found.add(str(address))
    except OSError:
        pass
    return sorted(found)
