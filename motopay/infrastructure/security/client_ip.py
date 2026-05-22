from __future__ import annotations

from fastapi import Request

from motopay.config import get_settings


def _trusted_proxy_ips() -> frozenset[str]:
    raw = get_settings().trusted_proxy_ips
    return frozenset(ip.strip() for ip in raw.split(",") if ip.strip())


def get_client_ip(request: Request) -> str:
    """IP do cliente. Só usa X-Forwarded-For/X-Real-IP se a conexão direta vier de proxy confiável."""
    direct = request.client.host if request.client else "unknown"
    trusted = _trusted_proxy_ips()
    if not trusted or direct not in trusted:
        return direct

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return direct
