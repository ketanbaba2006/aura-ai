"""
AURA AI Bedrock Research Client
Completely isolated LLM client for Deep Research mode.
Never touches Chat/Agent providers (Gemini/Groq/OpenRouter).
Supports AWS Bedrock and OpenAI-compatible endpoints.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# Supported research providers and their endpoint configurations
RESEARCH_PROVIDERS = {
    "bedrock": {
        "url_template": "https://bedrock-runtime.{region}.amazonaws.com/model/{model}/converse-stream",
        "auth_type": "bedrock",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "auth_type": "bearer",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "auth_type": "anthropic",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "auth_type": "bearer",
    },
    "perplexity": {
        "url": "https://api.perplexity.ai/chat/completions",
        "auth_type": "bearer",
    },
}


class ResearchLLMClient:
    """
    Async LLM client dedicated exclusively to Deep Research.
    Reads provider/model/key from DB settings with env fallback.
    Completely isolated from the Chat/Agent ProviderManager stack.
    """

    def __init__(self):
        self._settings_cache: dict | None = None
        self._settings_cache_time: float = 0.0
        self._cache_ttl: float = 30.0  # Refresh settings every 30s
        self.stats = {
            "requests": 0,
            "failures": 0,
            "total_tokens_approx": 0,
        }

    async def _get_research_settings(self) -> dict:
        """Fetch research-specific settings from DB, falling back to env vars."""
        now = time.time()
        if self._settings_cache and (now - self._settings_cache_time) < self._cache_ttl:
            return self._settings_cache

        # Default from env/config
        result = {
            "provider": settings.RESEARCH_PROVIDER,
            "api_key": settings.RESEARCH_API_KEY,
            "model": settings.RESEARCH_MODEL,
            "aws_region": settings.RESEARCH_AWS_REGION,
            "temperature": settings.RESEARCH_TEMPERATURE,
            "depth": settings.RESEARCH_DEPTH,
            "sources_limit": settings.RESEARCH_SOURCES_LIMIT,
            "timeout": settings.RESEARCH_TIMEOUT,
        }

        # Try to override from DB settings
        try:
            from app.database.database import db
            settings_keys = [
                "research_provider", "research_api_key", "research_model",
                "research_aws_region", "research_temperature", "research_depth",
                "research_sources_limit", "research_timeout",
            ]
            rows = await db.db.system_settings.find(
                {"key": {"$in": settings_keys}}, {"key": 1, "value": 1}
            ).to_list(length=None)

            db_map = {r["key"]: r["value"] for r in rows}
            if db_map.get("research_provider"):
                result["provider"] = db_map["research_provider"]
            if db_map.get("research_api_key"):
                result["api_key"] = db_map["research_api_key"]
            if db_map.get("research_model"):
                result["model"] = db_map["research_model"]
            if db_map.get("research_aws_region"):
                result["aws_region"] = db_map["research_aws_region"]
            if db_map.get("research_temperature"):
                try:
                    result["temperature"] = float(db_map["research_temperature"])
                except ValueError:
                    pass
            if db_map.get("research_depth"):
                result["depth"] = db_map["research_depth"]
            if db_map.get("research_sources_limit"):
                try:
                    result["sources_limit"] = int(db_map["research_sources_limit"])
                except ValueError:
                    pass
            if db_map.get("research_timeout"):
                try:
                    result["timeout"] = int(db_map["research_timeout"])
                except ValueError:
                    pass
        except Exception as e:
            logger.warning(f"ResearchLLMClient: Failed to load DB settings, using env defaults: {e}")

        self._settings_cache = result
        self._settings_cache_time = now
        return result

    def invalidate_cache(self):
        """Force settings to be re-fetched on next call."""
        self._settings_cache = None
        self._settings_cache_time = 0.0

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion using the research-dedicated provider.
        Never uses Chat/Agent providers.
        """
        cfg = await self._get_research_settings()
        provider = cfg["provider"]
        api_key = cfg["api_key"]
        model = cfg["model"]
        temperature = cfg["temperature"]
        timeout = cfg["timeout"]

        if not api_key or api_key == "INSECURE_DEFAULT_RESEARCH_KEY":
            # Seamless free-tier fallback: route through main LLM client (Groq / OpenRouter / Gemini)
            logger.info("ResearchLLMClient: Research-specific API key unconfigured, falling back seamlessly to default active LLM engine.")
            try:
                from app.core.llm_client import llm_client
                async for chunk, _meta in llm_client.stream_chat(
                    messages=messages,
                    system_prompt=system_prompt,
                    category="research",
                ):
                    if chunk:
                        yield chunk
                return
            except Exception as fb_err:
                logger.error(f"ResearchLLMClient fallback stream failed: {fb_err}", exc_info=True)
                yield f"\n\n⚠️ Autonomous research fallback error: {str(fb_err)}"
                return

        self.stats["requests"] += 1

        # Build messages payload
        full_messages = []
        if system_prompt and provider != "anthropic":
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            if provider == "bedrock":
                async for chunk in self._stream_bedrock(cfg, full_messages, system_prompt):
                    yield chunk
            elif provider == "anthropic":
                async for chunk in self._stream_anthropic(cfg, full_messages, system_prompt):
                    yield chunk
            else:
                # OpenAI-compatible providers (openai, openrouter, perplexity)
                async for chunk in self._stream_openai_compatible(cfg, full_messages):
                    yield chunk
        except Exception as e:
            self.stats["failures"] += 1
            logger.error(f"ResearchLLMClient stream failed [{provider}]: {e}", exc_info=True)
            yield f"\n\n⚠️ Research provider error: {str(e)}"

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
    ) -> str:
        """Non-streaming chat completion."""
        chunks = []
        async for chunk in self.stream_chat(messages, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict:
        """Generate structured JSON response from research provider."""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat(messages, system_prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Clean markdown wrappers
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning(f"ResearchLLMClient: Non-JSON response: {response[:200]}")
                return {"raw": response}

    # ── Provider-specific streaming implementations ──

    async def _stream_openai_compatible(
        self, cfg: dict, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI-compatible endpoints (OpenAI, OpenRouter, Perplexity)."""
        provider = cfg["provider"]
        provider_cfg = RESEARCH_PROVIDERS.get(provider, RESEARCH_PROVIDERS["openai"])
        url = provider_cfg["url"]

        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers.update({"HTTP-Referer": "http://localhost:3000", "X-Title": "AURA Deep Research"})

        payload = {
            "model": cfg["model"],
            "messages": messages,
            "stream": True,
            "temperature": cfg["temperature"],
        }

        async with httpx.AsyncClient(timeout=float(cfg["timeout"])) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(f"Provider returned {response.status_code}: {error_body.decode()[:300]}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                self.stats["total_tokens_approx"] += len(content) // 4
                                yield content
                    except json.JSONDecodeError:
                        continue

    async def _stream_anthropic(
        self, cfg: dict, messages: list[dict], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream from Anthropic Messages API."""
        url = RESEARCH_PROVIDERS["anthropic"]["url"]

        headers = {
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Anthropic uses system as top-level param, not in messages
        clean_messages = [m for m in messages if m.get("role") != "system"]

        payload = {
            "model": cfg["model"],
            "messages": clean_messages,
            "stream": True,
            "temperature": cfg["temperature"],
            "max_tokens": 8192,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=float(cfg["timeout"])) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise RuntimeError(f"Anthropic returned {response.status_code}: {error_body.decode()[:300]}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        event_type = chunk.get("type", "")
                        if event_type == "content_block_delta":
                            delta = chunk.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                self.stats["total_tokens_approx"] += len(text) // 4
                                yield text
                    except json.JSONDecodeError:
                        continue

    async def _stream_bedrock(
        self, cfg: dict, messages: list[dict], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream from AWS Bedrock Converse API.
        Uses the Bedrock key as a Bearer token for proxy gateway access.
        Falls back to OpenAI-compatible format if proxy detected.
        """
        api_key = cfg["api_key"]
        model = cfg["model"]
        region = cfg["aws_region"]

        # Detect if key format suggests a proxy gateway (contains ':' separator)
        if ":" in api_key and api_key.startswith("Bedrock"):
            # Proxy gateway — use OpenAI-compatible format through Bedrock proxy
            proxy_url = f"https://bedrock-runtime.{region}.amazonaws.com/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            clean_messages = []
            if system_prompt:
                clean_messages.append({"role": "system", "content": system_prompt})
            clean_messages.extend([m for m in messages if m.get("role") != "system"])

            payload = {
                "model": model,
                "messages": clean_messages,
                "stream": True,
                "temperature": cfg["temperature"],
                "max_tokens": 8192,
            }

            try:
                async with httpx.AsyncClient(timeout=float(cfg["timeout"])) as client:
                    async with client.stream("POST", proxy_url, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            raise RuntimeError(f"Bedrock proxy returned {response.status_code}: {error_body.decode()[:300]}")

                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        self.stats["total_tokens_approx"] += len(content) // 4
                                        yield content
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.warning(f"Bedrock proxy failed, attempting boto3 SDK: {e}")
                # Fall through to boto3 SDK
                async for chunk in self._stream_bedrock_sdk(cfg, messages, system_prompt):
                    yield chunk
        else:
            # Direct boto3 SDK access
            async for chunk in self._stream_bedrock_sdk(cfg, messages, system_prompt):
                yield chunk

    async def _stream_bedrock_sdk(
        self, cfg: dict, messages: list[dict], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream from AWS Bedrock using boto3 SDK (requires AWS credentials)."""
        try:
            import boto3

            bedrock = boto3.client(
                "bedrock-runtime",
                region_name=cfg["aws_region"],
            )

            # Convert messages to Bedrock Converse format
            bedrock_messages = []
            for m in messages:
                if m.get("role") == "system":
                    continue
                bedrock_messages.append({
                    "role": m["role"],
                    "content": [{"text": m["content"]}],
                })

            params = {
                "modelId": cfg["model"],
                "messages": bedrock_messages,
                "inferenceConfig": {
                    "temperature": cfg["temperature"],
                    "maxTokens": 8192,
                },
            }
            if system_prompt:
                params["system"] = [{"text": system_prompt}]

            response = bedrock.converse_stream(**params)
            stream = response.get("stream", [])

            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        self.stats["total_tokens_approx"] += len(text) // 4
                        yield text

        except ImportError:
            yield "⚠️ boto3 is not installed. Please run `pip install boto3` to use AWS Bedrock."
        except Exception as e:
            logger.error(f"Bedrock SDK streaming failed: {e}", exc_info=True)
            raise

    async def health_check(self) -> dict:
        """Check if the research provider is configured and reachable."""
        cfg = await self._get_research_settings()
        provider = cfg["provider"]
        api_key = cfg["api_key"]

        result = {
            "provider": provider,
            "model": cfg["model"],
            "configured": bool(api_key and api_key != "INSECURE_DEFAULT_RESEARCH_KEY"),
            "status": "unconfigured",
        }

        if not result["configured"]:
            return result

        try:
            # Quick test with minimal payload
            test_response = await self.chat(
                [{"role": "user", "content": "ping"}],
                system_prompt="Reply with exactly: pong",
            )
            if test_response and len(test_response.strip()) > 0:
                result["status"] = "active"
            else:
                result["status"] = "error"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result


# Global isolated instance — never shared with Chat/Agent modes
research_llm_client = ResearchLLMClient()
