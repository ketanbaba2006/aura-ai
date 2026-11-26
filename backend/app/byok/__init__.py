"""
AURA AI — BYOK (Bring Your Own Key) subsystem.

Dynamic, provider-agnostic gateway integration:
the user supplies an API key + gateway base URL, AURA connects to *that exact
gateway*, authenticates, discovers models, and routes chat through them.

Nothing in here hardcodes a provider or a model list.
"""

from app.byok.gateway_url import (  # noqa: F401
    GatewayUrlError,
    NormalizedGateway,
    normalize_gateway_url,
    join_endpoint,
)
from app.byok.ssrf import SsrfBlockedError, validate_outbound_url  # noqa: F401
