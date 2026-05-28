#!/usr/bin/env python3
"""Retorna o IPv4 da interface usada para acessar a rede local (Wi‑Fi/LAN)."""
from __future__ import annotations

import socket
import sys


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return ""


if __name__ == "__main__":
    sys.stdout.write(get_lan_ip())
