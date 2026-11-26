"""
Gateway URL normalization.

Rules (BYOK spec §2):
  - remove trailing slashes
  - prevent duplicated /v1
  - preserve the user's intended path
  - support URLs that already contain /v1
  - support any OpenAI-compatible gateway
  - DO NOT blindly append /v1

Instead of guessing, we compute an ordered list of *candidate* base URLs.
Discovery probes them and the one that answers becomes the resolved base URL,
which is then used for every subsequent request on that connection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


class GatewayUrlError(ValueError):
    """Raised when a user-supplied gateway URL cannot be used safely."""


# A path segment that looks like an API version: v1, v2, v1beta, v1alpha1, beta ...
_VERSION_SEGMENT = re.compile(r"^v\d+[a-z0-9_-]*$", re.IGNORECASE)

# Endpoint suffixes users commonly paste in full. They are stripped so the
# stored value is a *base* URL, while the intended prefix is preserved.
_KNOWN_ENDPOINT_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("chat", "completions"),
    ("completions",),
    ("responses",),
    ("embeddings",),
    ("models",),
)

_MAX_URL_LENGTH = 2000


@dataclass
class NormalizedGateway:
    """Result of normalizing a user-supplied gateway URL."""

    base_url: str
    """Canonical base URL: scheme://host[:port]/path, no trailing slash."""

    scheme: str
    host: str
    port: int | None
    path: str
    candidate_base_urls: list[str] = field(default_factory=list)
    """Ordered bases to probe. First entry is always ``base_url``."""

    notes: list[str] = field(default_factory=list)
    """Human-readable description of what was changed (never contains secrets)."""

    has_version_segment: bool = False
    stripped_endpoint: str | None = None

    @property
    def origin(self) -> str:
        netloc = self.host if self.port is None else f"{self.host}:{self.port}"
        return f"{self.scheme}://{netloc}"


def _collapse_repeated_versions(segments: list[str]) -> tuple[list[str], bool]:
    """Collapse accidental `/v1/v1` (or `/v1beta/v1beta`) duplication."""
    out: list[str] = []
    changed = False
    for seg in segments:
        if (
            out
            and _VERSION_SEGMENT.match(seg)
            and out[-1].lower() == seg.lower()
        ):
            changed = True
            continue
        out.append(seg)
    return out, changed


def _strip_endpoint_suffix(segments: list[str]) -> tuple[list[str], str | None]:
    """Remove a trailing well-known endpoint path so we keep only the base."""
    lowered = [s.lower() for s in segments]
    for suffix in _KNOWN_ENDPOINT_SUFFIXES:
        n = len(suffix)
        if n <= len(lowered) and tuple(lowered[-n:]) == suffix:
            # Never strip the whole path away into nothing meaningful if the
            # suffix *is* the entire path and there is no version prefix — e.g.
            # "https://host/models" -> base "https://host" is still correct.
            return segments[:-n], "/" + "/".join(suffix)
    return segments, None


def normalize_gateway_url(raw: str) -> NormalizedGateway:
    """Normalize a user-supplied gateway URL into a safe canonical base URL."""
    if raw is None:
        raise GatewayUrlError("Gateway URL is required.")

    value = raw.strip()
    if not value:
        raise GatewayUrlError("Gateway URL is required.")
    if len(value) > _MAX_URL_LENGTH:
        raise GatewayUrlError("Gateway URL is too long.")
    if any(ch in value for ch in ("\n", "\r", "\t", " ")):
        raise GatewayUrlError("Gateway URL must not contain whitespace.")

    notes: list[str] = []

    # Accept "api.example.com/v1" by assuming HTTPS (never downgrade to HTTP).
    if "://" not in value:
        value = "https://" + value
        notes.append("Assumed https:// scheme.")

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise GatewayUrlError(
            f"Unsupported URL scheme '{parts.scheme}'. Use http or https."
        )

    if parts.username or parts.password:
        raise GatewayUrlError(
            "Credentials must not be embedded in the gateway URL. "
            "Provide the API key in the API Key field instead."
        )

    host = (parts.hostname or "").strip().lower()
    if not host:
        raise GatewayUrlError("Gateway URL is missing a host name.")

    try:
        port = parts.port
    except ValueError as exc:  # invalid port
        raise GatewayUrlError("Gateway URL has an invalid port.") from exc
    if port is not None and not (0 < port < 65536):
        raise GatewayUrlError("Gateway URL has an invalid port.")

    if parts.query or parts.fragment:
        notes.append("Removed query string / fragment from the base URL.")

    segments = [seg for seg in parts.path.split("/") if seg not in ("", ".")]
    if any(seg == ".." for seg in segments):
        raise GatewayUrlError("Gateway URL must not contain '..' path segments.")

    segments, stripped = _strip_endpoint_suffix(segments)
    if stripped:
        notes.append(f"Detected endpoint path '{stripped}' and kept the base URL.")

    segments, collapsed = _collapse_repeated_versions(segments)
    if collapsed:
        notes.append("Collapsed a duplicated version segment (e.g. /v1/v1 -> /v1).")

    path = "/" + "/".join(segments) if segments else ""
    base_url = urlunsplit((scheme, parts.netloc.lower(), path, "", ""))
    base_url = base_url.rstrip("/")

    has_version = bool(segments) and bool(_VERSION_SEGMENT.match(segments[-1]))

    # Candidates: exactly what the user gave first. Only if there is no version
    # segment anywhere in the path do we *offer* a "/v1" variant as a fallback
    # probe — we never rewrite the user's URL silently.
    candidates = [base_url]
    path_has_any_version = any(_VERSION_SEGMENT.match(s) for s in segments)
    if not path_has_any_version:
        candidates.append(base_url + "/v1")
        if stripped:
            # e.g. user pasted ".../v1/models" -> already versioned; but for
            # ".../models" the un-versioned base is tried first, then /v1.
            pass

    return NormalizedGateway(
        base_url=base_url,
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        candidate_base_urls=candidates,
        notes=notes,
        has_version_segment=has_version,
        stripped_endpoint=stripped,
    )


def join_endpoint(base_url: str, endpoint: str) -> str:
    """Join a resolved base URL with an endpoint without duplicating segments."""
    base = base_url.rstrip("/")
    suffix = endpoint.strip("/")
    if not suffix:
        return base
    base_segments = [s for s in urlsplit(base).path.split("/") if s]
    suffix_segments = suffix.split("/")
    # Guard against ".../v1/models" + "models"
    if base_segments and [s.lower() for s in base_segments[-len(suffix_segments):]] == [
        s.lower() for s in suffix_segments
    ]:
        return base
    return f"{base}/{suffix}"


def mask_url_for_log(url: str) -> str:
    """Return a log-safe rendering of a URL (no query string, no credentials)."""
    try:
        p = urlsplit(url)
        netloc = p.hostname or ""
        if p.port:
            netloc = f"{netloc}:{p.port}"
        return urlunsplit((p.scheme, netloc, p.path, "", ""))
    except Exception:
        return "<unparsable-url>"
