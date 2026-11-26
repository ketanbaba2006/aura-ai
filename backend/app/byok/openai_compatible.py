"""
OpenAICompatibleProvider — the single generic adapter used for every BYOK
gateway (spec §9).

Speaks the OpenAI-compatible surface:
  GET  {base}/models
  POST {base}/chat/completions   (streaming and non-streaming)

Everything is dynamic: no provider name, model name or model list is hardcoded.
Every request is SSRF-validated (including each redirect hop) and bounded by
connect / read timeouts and a response size limit. Authorization headers are
never logged.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import httpx

from app.byok.gateway_url import join_endpoint, mask_url_for_log
from app.byok.ssrf import SsrfBlockedError, validate_outbound_url
from app.config import settings

logger = logging.getLogger(__name__)

_REDIRECT_CODES = {301, 302, 303, 307, 308}


class GatewayError(Exception):
    """A user-presentable gateway failure. Never contains the API key."""

    def __init__(self, message: str, *, kind: str = "gateway_error", status: int | None = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status = status


@dataclass
class ModelsResult:
    """Outcome of a model-discovery attempt against one gateway."""

    ok: bool
    resolved_base_url: str | None = None
    raw_models: list[dict] = field(default_factory=list)
    error: str | None = None
    error_kind: str | None = None
    status: int | None = None
    server_header: str | None = None
    attempts: list[dict] = field(default_factory=list)


def describe_http_status(status: int, *, endpoint: str) -> tuple[str, str]:
    """Map an HTTP status to (human message, kind). Never includes the key."""
    if status in (401,):
        return ("Authentication failed — the gateway rejected the API key.", "auth_failed")
    if status == 403:
        return (
            "Unauthorized — the API key is valid but not permitted to use this gateway "
            "or model.",
            "forbidden",
        )
    if status == 404:
        return (
            f"Provider returned 404 — no {endpoint} endpoint at this base URL.",
            "not_found",
        )
    if status == 405:
        return (
            f"Provider returned 405 — {endpoint} does not accept this request method.",
            "not_found",
        )
    if status == 429:
        return ("Provider returned 429 — rate limit or quota exceeded.", "rate_limited")
    if status in (402, 403):
        return ("Provider returned 402 — billing or quota problem.", "quota")
    if status == 400:
        return ("Provider returned 400 — the request was rejected as invalid.", "bad_request")
    if 500 <= status < 600:
        return (f"Provider returned {status} — the gateway reported a server error.", "server_error")
    return (f"Provider returned {status}.", "gateway_error")


def describe_transport_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, SsrfBlockedError):
        return (str(exc), "blocked")
    if isinstance(exc, httpx.ConnectTimeout):
        return ("Gateway unreachable — the connection timed out.", "timeout")
    if isinstance(exc, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return ("Gateway timed out while responding.", "timeout")
    if isinstance(exc, httpx.ConnectError):
        return ("Gateway unreachable — the connection was refused or DNS failed.", "unreachable")
    if isinstance(exc, httpx.TooManyRedirects):
        return ("Invalid base URL — the gateway redirected too many times.", "invalid_url")
    if isinstance(exc, httpx.InvalidURL):
        return ("Invalid base URL.", "invalid_url")
    if isinstance(exc, httpx.HTTPError):
        return ("Gateway unreachable — the network request failed.", "unreachable")
    return ("Gateway request failed unexpectedly.", "gateway_error")


def extract_models(payload: Any) -> list[dict] | None:
    """Pull a model list out of any reasonable /models response shape."""
    container: Any = None

    if isinstance(payload, list):
        container = payload
    elif isinstance(payload, dict):
        for key in ("data", "models", "results", "items", "model_list"):
            value = payload.get(key)
            if isinstance(value, list):
                container = value
                break
            if isinstance(value, dict):
                nested = value.get("models") or value.get("data")
                if isinstance(nested, list):
                    container = nested
                    break
        if container is None:
            # Mapping of id -> metadata, e.g. {"gpt-4o": {...}}
            if payload and all(isinstance(v, dict) for v in payload.values()):
                container = [
                    {**v, "id": v.get("id") or k} for k, v in payload.items()
                ]

    if container is None:
        return None

    models: list[dict] = []
    for entry in container:
        if isinstance(entry, str):
            models.append({"id": entry})
        elif isinstance(entry, dict):
            model_id = (
                entry.get("id")
                or entry.get("model")
                or entry.get("name")
                or entry.get("model_id")
                or entry.get("modelId")
            )
            if not model_id:
                continue
            normalized = dict(entry)
            normalized["id"] = str(model_id)
            models.append(normalized)

    return models


class OpenAICompatibleProvider:
    """Generic adapter for any OpenAI-compatible gateway."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        organization_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
        request_timeout: float | None = None,
        stream_timeout: float | None = None,
        allow_private_networks: bool | None = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self.organization_id = (organization_id or "").strip() or None
        self.extra_headers = {
            str(k): str(v) for k, v in (extra_headers or {}).items() if str(k).strip()
        }
        self.request_timeout = request_timeout or settings.BYOK_REQUEST_TIMEOUT
        self.stream_timeout = stream_timeout or settings.BYOK_STREAM_TIMEOUT
        self.allow_private_networks = allow_private_networks

    # ── headers ───────────────────────────────────────────────
    def _headers(self, *, stream: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "text/event-stream" if stream else "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AURA-AI-BYOK/1.0",
        }
        headers.update(self.extra_headers)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self.organization_id:
            headers.setdefault("OpenAI-Organization", self.organization_id)
        return headers

    @staticmethod
    def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
        """Redact anything credential-bearing before it can reach a log."""
        redacted = {}
        for key, value in headers.items():
            if key.lower() in {"authorization", "x-api-key", "api-key", "openai-organization", "proxy-authorization"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = value
        return redacted

    def _timeout(self, total: float) -> httpx.Timeout:
        return httpx.Timeout(
            total, connect=min(settings.BYOK_CONNECT_TIMEOUT, total), read=total
        )


    # ── low-level request with per-hop SSRF validation ────────
    async def _send(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Send a request, re-validating every redirect hop before following."""
        current = url
        for _ in range(settings.BYOK_MAX_REDIRECTS + 1):
            await validate_outbound_url(
                current, allow_private=self.allow_private_networks
            )
            request = client.build_request(
                method, current, headers=headers, json=json_body
            )
            response = await client.send(request, stream=stream)
            if response.status_code in _REDIRECT_CODES:
                location = response.headers.get("location")
                if stream:
                    await response.aclose()
                else:
                    await response.aread()
                    await response.aclose()
                if not location:
                    raise GatewayError(
                        "Invalid base URL — the gateway redirected without a target.",
                        kind="invalid_url",
                        status=response.status_code,
                    )
                current = str(httpx.URL(current).join(location))
                continue
            return response

        raise GatewayError(
            "Invalid base URL — too many redirects from the gateway.",
            kind="invalid_url",
        )


    async def _read_bounded(self, response: httpx.Response) -> bytes:
        body = await response.aread()
        if len(body) > settings.BYOK_MAX_RESPONSE_BYTES:
            raise GatewayError(
                "Gateway response exceeded the allowed size limit.",
                kind="too_large",
            )
        return body

    @staticmethod
    def _error_detail(body: bytes) -> str | None:
        """Extract a short provider-supplied error message, if any."""
        if not body:
            return None
        try:
            payload = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            text = body.decode("utf-8", "replace").strip()
            if not text or text.lstrip().startswith("<"):
                return None
            return text[:200]
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("code") or error.get("type")
                if message:
                    return str(message)[:200]
            if isinstance(error, str):
                return error[:200]
            for key in ("message", "detail", "detail_message", "msg"):
                if isinstance(payload.get(key), str):
                    return payload[key][:200]
        return None

    def _redact(self, text: str | None) -> str | None:
        """Belt-and-braces: strip the key from anything echoed back by a gateway."""
        if not text:
            return text
        cleaned = text
        if self._api_key and len(self._api_key) >= 6:
            cleaned = cleaned.replace(self._api_key, "<redacted>")
            cleaned = cleaned.replace(self._api_key[-8:], "<redacted>")
        return cleaned


    # ── model discovery ───────────────────────────────────────
    async def list_models(self, candidate_base_urls: list[str] | None = None) -> ModelsResult:
        """GET {base}/models across candidate bases; first success wins."""
        candidates = [c.rstrip("/") for c in (candidate_base_urls or [self.base_url]) if c]
        if not candidates:
            return ModelsResult(ok=False, error="Invalid base URL.", error_kind="invalid_url")

        result = ModelsResult(ok=False)
        headers = self._headers()
        auth_failure: ModelsResult | None = None

        async with httpx.AsyncClient(
            timeout=self._timeout(self.request_timeout), follow_redirects=False
        ) as client:
            for base in candidates:
                url = join_endpoint(base, "models")
                attempt: dict = {"base_url": base, "url": mask_url_for_log(url)}
                try:
                    response = await self._send(client, "GET", url, headers=headers)
                except (GatewayError, SsrfBlockedError, httpx.HTTPError) as exc:
                    if isinstance(exc, GatewayError):
                        message, kind = exc.message, exc.kind
                    else:
                        message, kind = describe_transport_error(exc)
                    attempt.update({"ok": False, "error": message, "kind": kind})
                    result.attempts.append(attempt)
                    result.error, result.error_kind = message, kind
                    if kind in {"blocked", "unreachable", "timeout"}:
                        break  # network-level failure: other paths won't help
                    continue

                status = response.status_code
                body = await self._read_bounded(response)
                await response.aclose()
                attempt["status"] = status
                result.server_header = response.headers.get("server") or result.server_header

                if status == 200:
                    try:
                        payload = json.loads(body.decode("utf-8", "replace"))
                    except Exception:
                        message = "Models endpoint returned a response AURA could not parse."
                        attempt.update({"ok": False, "error": message, "kind": "unparsable"})
                        result.attempts.append(attempt)
                        result.error, result.error_kind = message, "unparsable"
                        continue

                    models = extract_models(payload)
                    if models is None:
                        message = "Models endpoint returned an unexpected format."
                        attempt.update({"ok": False, "error": message, "kind": "unparsable"})
                        result.attempts.append(attempt)
                        result.error, result.error_kind = message, "unparsable"
                        continue

                    attempt.update({"ok": True, "count": len(models)})
                    result.attempts.append(attempt)
                    result.ok = True
                    result.resolved_base_url = base
                    result.raw_models = models[: settings.BYOK_MAX_MODELS]
                    result.error = None
                    result.error_kind = None
                    return result

                message, kind = describe_http_status(status, endpoint="/models")
                detail = self._redact(self._error_detail(body))
                if detail:
                    message = f"{message} ({detail})"
                attempt.update({"ok": False, "error": message, "kind": kind})
                result.attempts.append(attempt)
                result.error, result.error_kind, result.status = message, kind, status
                if kind in {"auth_failed", "forbidden"}:
                    # Auth problems are conclusive for this key; remember them but
                    # still let a different base prove the path was simply wrong.
                    auth_failure = ModelsResult(
                        ok=False, error=message, error_kind=kind, status=status
                    )

        if auth_failure is not None and result.error_kind not in {"auth_failed", "forbidden"}:
            result.error = auth_failure.error
            result.error_kind = auth_failure.error_kind
            result.status = auth_failure.status
        return result


    # ── chat ──────────────────────────────────────────────────
    def _chat_url(self) -> str:
        return join_endpoint(self.base_url, "chat/completions")

    @staticmethod
    def _build_body(
        model: str, messages: list[dict], *, stream: bool, params: dict | None
    ) -> dict:
        body: dict[str, Any] = {"model": model, "messages": messages}
        if stream:
            body["stream"] = True
        for key, value in (params or {}).items():
            if value is None or key in {"model", "messages", "stream"}:
                continue
            body[key] = value
        return body

    @staticmethod
    def _extract_text(payload: Any) -> str:
        """Pull assistant text out of a non-streaming completion payload."""
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0] if isinstance(choices[0], dict) else {}
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    ]
                    return "".join(parts)
                reasoning = message.get("reasoning_content") or message.get("reasoning")
                if isinstance(reasoning, str):
                    return reasoning
            if isinstance(choice.get("text"), str):
                return choice["text"]
            delta = choice.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]
        # Some gateways answer with a bare {"output_text": "..."} shape.
        for key in ("output_text", "content", "response", "text"):
            if isinstance(payload.get(key), str):
                return payload[key]
        return ""

    @staticmethod
    def _extract_delta(chunk: dict) -> str:
        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        choice = choices[0] if isinstance(choices[0], dict) else {}
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if isinstance(delta.get("reasoning_content"), str):
                return ""  # reasoning traces are not part of the answer body
        message = choice.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(choice.get("text"), str):
            return choice["text"]
        return ""


    async def complete(
        self, model: str, messages: list[dict], **params
    ) -> str:
        """Non-streaming chat completion. Returns the assistant text."""
        url = self._chat_url()
        body = self._build_body(model, messages, stream=False, params=params)
        async with httpx.AsyncClient(
            timeout=self._timeout(self.request_timeout), follow_redirects=False
        ) as client:
            try:
                response = await self._send(
                    client, "POST", url, headers=self._headers(), json_body=body
                )
            except GatewayError:
                raise
            except (SsrfBlockedError, httpx.HTTPError) as exc:
                message, kind = describe_transport_error(exc)
                raise GatewayError(message, kind=kind) from exc

            raw = await self._read_bounded(response)
            await response.aclose()

            if response.status_code != 200:
                message, kind = describe_http_status(
                    response.status_code, endpoint="/chat/completions"
                )
                detail = self._redact(self._error_detail(raw))
                if detail:
                    message = f"{message} ({detail})"
                raise GatewayError(message, kind=kind, status=response.status_code)

            try:
                payload = json.loads(raw.decode("utf-8", "replace"))
            except Exception as exc:
                raise GatewayError(
                    "The gateway returned a response AURA could not parse.",
                    kind="unparsable",
                ) from exc

            text = self._extract_text(payload)
            if not text:
                detail = self._redact(self._error_detail(raw))
                raise GatewayError(
                    f"The gateway returned an empty completion."
                    + (f" ({detail})" if detail else ""),
                    kind="empty_response",
                )
            return text


    async def stream(
        self, model: str, messages: list[dict], **params
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion with automatic non-streaming fallback."""
        url = self._chat_url()
        body = self._build_body(model, messages, stream=True, params=params)

        async with httpx.AsyncClient(
            timeout=self._timeout(self.stream_timeout), follow_redirects=False
        ) as client:
            try:
                response = await self._send(
                    client,
                    "POST",
                    url,
                    headers=self._headers(stream=True),
                    json_body=body,
                    stream=True,
                )
            except GatewayError:
                raise
            except (SsrfBlockedError, httpx.HTTPError) as exc:
                message, kind = describe_transport_error(exc)
                raise GatewayError(message, kind=kind) from exc

            if response.status_code != 200:
                raw = await self._read_bounded(response)
                await response.aclose()
                detail = self._redact(self._error_detail(raw)) or ""
                if response.status_code in (400, 404, 422, 501) and "stream" in detail.lower():
                    # Gateway rejects streaming: fall back transparently.
                    text = await self.complete(model, messages, **params)
                    if text:
                        yield text
                    return
                message, kind = describe_http_status(
                    response.status_code, endpoint="/chat/completions"
                )
                if detail:
                    message = f"{message} ({detail})"
                raise GatewayError(message, kind=kind, status=response.status_code)

            content_type = (response.headers.get("content-type") or "").lower()
            if "text/event-stream" not in content_type and "stream" not in content_type:
                # Gateway ignored `stream: true` and answered with a whole JSON body.
                raw = await self._read_bounded(response)
                await response.aclose()
                try:
                    payload = json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    payload = None
                text = self._extract_text(payload) if payload is not None else ""
                if text:
                    yield text
                    return
                raise GatewayError(
                    "The gateway returned an empty completion.", kind="empty_response"
                )

            emitted = False
            buffer = ""
            try:
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith(":"):
                        continue  # SSE comment / keep-alive
                    if line.startswith("event:"):
                        continue
                    if line.startswith("data:"):
                        payload_text = line[5:].strip()
                    else:
                        payload_text = line
                    if not payload_text or payload_text == "[DONE]":
                        if payload_text == "[DONE]":
                            break
                        continue
                    try:
                        chunk = json.loads(payload_text)
                    except Exception:
                        continue
                    if isinstance(chunk, dict) and chunk.get("error"):
                        detail = self._redact(self._error_detail(payload_text.encode()))
                        raise GatewayError(
                            f"The gateway reported an error mid-stream."
                            + (f" ({detail})" if detail else ""),
                            kind="stream_error",
                        )
                    delta = self._extract_delta(chunk) if isinstance(chunk, dict) else ""
                    if delta:
                        emitted = True
                        buffer += delta
                        yield delta
            finally:
                await response.aclose()

            if not emitted and not buffer:
                text = await self.complete(model, messages, **params)
                if text:
                    yield text


    # ── probes ────────────────────────────────────────────────
    async def probe_model(self, model: str) -> tuple[bool, str, bool]:
        """Send a minimal completion to prove a model id really works.

        Returns ``(ok, message, streaming_supported)``.
        """
        messages = [{"role": "user", "content": "ping"}]
        try:
            await self.complete(model, messages, max_tokens=1, temperature=0)
        except GatewayError as exc:
            return (False, exc.message, False)

        streaming = False
        try:
            async for _ in self.stream(model, messages, max_tokens=1, temperature=0):
                streaming = True
                break
        except GatewayError:
            streaming = False
        return (True, f"Model '{model}' responded successfully.", streaming)

    async def probe_auth(self) -> tuple[bool, str, str | None]:
        """Cheap auth probe used when /models is unavailable."""
        url = join_endpoint(self.base_url, "models")
        async with httpx.AsyncClient(
            timeout=self._timeout(settings.BYOK_CONNECT_TIMEOUT + 5), follow_redirects=False
        ) as client:
            try:
                response = await self._send(client, "GET", url, headers=self._headers())
            except GatewayError as exc:
                return (False, exc.message, exc.kind)
            except (SsrfBlockedError, httpx.HTTPError) as exc:
                message, kind = describe_transport_error(exc)
                return (False, message, kind)
            body = await self._read_bounded(response)
            await response.aclose()
            if response.status_code == 200:
                return (True, "Authenticated.", None)
            message, kind = describe_http_status(response.status_code, endpoint="/models")
            detail = self._redact(self._error_detail(body))
            if detail:
                message = f"{message} ({detail})"
            return (False, message, kind)

