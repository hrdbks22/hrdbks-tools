"""Display local IPv4 interfaces and likely private LAN CIDRs.

This helper only discovers and reports network interfaces. It does not change
router settings, firewall rules, or automatically trust a newly detected network.
For production, confirm the office subnet with the network administrator.
"""
from __future__ import annotations

import ipaddress
import socket


def main() -> None:
    candidates: set[str] = set()
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for info in infos:
            address = info[4][0]
            ip = ipaddress.ip_address(address)
            if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                candidates.add(str(ip))
    except OSError as exc:
        print(f"Gagal membaca interface jaringan: {exc}")

    # Determine the preferred outbound interface without sending application data.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 80))  # TEST-NET address; UDP connect does not send packets.
        address = probe.getsockname()[0]
        probe.close()
        ip = ipaddress.ip_address(address)
        if ip.is_private and not ip.is_loopback:
            candidates.add(str(ip))
    except OSError:
        pass

    if not candidates:
        print("Tidak menemukan IPv4 private. Periksa koneksi LAN/Wi-Fi server.")
        return

    print("Alamat IPv4 private yang terdeteksi:")
    for address in sorted(candidates):
        print(f"  - {address}")
    print("\nCatatan: subnet/CIDR kantor harus dikonfirmasi, jangan menebak /24.")
    print("Masukkan CIDR yang benar ke aturan allow Nginx dan firewall.")


if __name__ == "__main__":
    main()
