"""Validacion de URL: scheme + host whitelist + path rule + anti-SSRF."""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from app.constants.platforms import (
    ALLOWED_HOSTS,
    PLATFORM_PATH_RULES,
    platform_for_host,
)


class UrlValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedUrl:
    raw: str
    host: str
    path: str
    platform: str


_PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    ]
]


def _resolve_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if any(ip in net for net in _PRIVATE_NETS):
            return False
    return True


def validate_url(raw: str) -> ValidatedUrl:
    if not raw or not isinstance(raw, str):
        raise UrlValidationError("empty url")
    parsed = urlparse(raw.strip())
    if parsed.scheme != "https":
        raise UrlValidationError("scheme must be https")
    host = (parsed.netloc or "").lower()
    if not host or host not in ALLOWED_HOSTS:
        raise UrlValidationError(f"host not allowed: {host}")
    rule = PLATFORM_PATH_RULES.get(host)
    if rule and not rule({"path": parsed.path}):
        raise UrlValidationError(f"path not allowed for {host}: {parsed.path}")
    if not _resolve_is_public(host):
        raise UrlValidationError(f"host resolves to private IP: {host}")
    return ValidatedUrl(
        raw=raw,
        host=host,
        path=parsed.path,
        platform=platform_for_host(host),
    )
