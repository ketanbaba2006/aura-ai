"""
SSRF protection for BYOK outbound requests (spec §18).

Every outbound request to a user-supplied gateway is validated:
  - scheme must be http/https
  - the host is resolved and *every* resolved address is checked
  - loopback, private, link-local, reserved, multicast and unspecified ranges
    are blocked unless an operator explicitly opts in via
    AURA_BYOK_ALLOW_PRIVATE_NETWORKS=true
  - redirects are re-validated hop by hop (see openai_compatible.py)

The guard is intentionally applied at request time (not only at save time) so a
DNS record that later flips to a private address cannot be used as a bypass.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.config import settings

logger = logging.getLogger(__name__)


class SsrfBlockedError(Exception):
    """Raised when a URL points at a target we refuse to contact."""


# Hosts that commonly front cloud instance metadata services.
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "instance-data",
    "instance-data.ec2.internal",
}

_BLOCKED_HOST_SUFFIXES = (
    ".internal",
    ".local",
    ".localdomain",
    ".cluster.local",
)


@dataclass
class ValidatedTarget:
    url: str
    scheme: str
    host: str
    port: int
    addresses: list[str]


def _is_disallowed_ip(ip: ipaddress._BaseAddress) -> str | None:
    """Return a human-readable reason if the address must not be contacted."""
    if ip.is_unspecified:
        return "unspecified address"
    if ip.is_loopback:
        return "loopback address"
    if ip.is_link_local:
        return "link-local address"
    if ip.is_multicast:
        return "multicast address"
    if getattr(ip, "is_reserved", False):
        return "reserved address"
    if ip.is_private:
        return "private network address"
    # IPv6 transition ranges that can smuggle private IPv4 targets.
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped or getattr(ip, "sixtofour", None)
        if mapped is not None:
            return _is_disallowed_ip(mapped)
        teredo = getattr(ip, "teredo", None)
        if teredo:
            return _is_disallowed_ip(teredo[1])
    return None


async def _resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(
            host, port, proto=socket.IPPROTO_TCP, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise SsrfBlockedError(
            f"Gateway unreachable — host '{host}' could not be resolved."
        ) from exc
    except OSError as exc:
        raise SsrfBlockedError(
            f"Gateway unreachable — DNS lookup failed for '{host}'."
        ) from exc

    addresses: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr and isinstance(sockaddr[0], str):
            addresses.append(sockaddr[0])
    if not addresses:
        raise SsrfBlockedError(
            f"Gateway unreachable — host '{host}' has no usable address."
        )
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(addresses))


async def validate_outbound_url(url: str, *, allow_private: bool | None = None) -> ValidatedTarget:
    """Validate a URL for outbound BYOK traffic. Raises SsrfBlockedError."""
    allow_private = (
        settings.BYOK_ALLOW_PRIVATE_NETWORKS if allow_private is None else allow_private
    )

    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise SsrfBlockedError(f"Unsupported URL scheme '{parts.scheme or '?'}'.")

    if settings.BYOK_REQUIRE_HTTPS and scheme != "https" and not allow_private:
        raise SsrfBlockedError("Only https:// gateway URLs are permitted.")

    host = (parts.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise SsrfBlockedError("Gateway URL is missing a host name.")

    try:
        port = parts.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise SsrfBlockedError("Gateway URL has an invalid port.") from exc

    literal_ip: ipaddress._BaseAddress | None = None
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is None and not allow_private:
        if host in _BLOCKED_HOSTNAMES or host == "localhost":
            raise SsrfBlockedError(
                "Blocked: internal host names are not allowed as BYOK gateways."
            )
        if host.endswith(_BLOCKED_HOST_SUFFIXES):
            raise SsrfBlockedError(
                "Blocked: internal-only domain suffixes are not allowed as BYOK gateways."
            )

    if literal_ip is not None:
        addresses = [str(literal_ip)]
    else:
        addresses = await _resolve(host, port)

    if not allow_private:
        for addr in addresses:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                raise SsrfBlockedError("Gateway resolved to an unusable address.")
            reason = _is_disallowed_ip(ip)
            if reason:
                raise SsrfBlockedError(
                    f"Blocked: the gateway resolves to a {reason}. "
                    "Requests to internal or private networks are not permitted."
                )

    return ValidatedTarget(
        url=url, scheme=scheme, host=host, port=port, addresses=addresses
    )
