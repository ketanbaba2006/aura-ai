"""
AURA AI Identity System
Centralized application identity, model metadata, and creator information.
"""

from dataclasses import dataclass, field
from typing import Optional
from app.config import settings


@dataclass
class ModelMetadata:
    """Actual model information for a response."""
    provider: str
    model_id: str
    model_display_name: Optional[str] = None
    selection_source: str = "auto"  # "user_selected", "auto", "fallback"
    requested_model: Optional[str] = None
    actual_resolved_model: Optional[str] = None
    fallback_status: bool = False
    fallback_from: Optional[str] = None
    request_status: str = "success"  # "success", "fallback", "error"
    verified_capabilities: list[str] = field(default_factory=list)


@dataclass
class ApplicationIdentity:
    """Centralized application identity configuration."""
    name: str = "Aura AI"
    creator: str = "Ketanbaba"
    version: str = "0.1.0"
    domain: str = "auraainet.xyz"
    description: str = ""
    purpose: str = ""
    supported_languages: list[str] = field(default_factory=list)
    available_capabilities: list[str] = field(default_factory=list)
    supported_providers: list[str] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "ApplicationIdentity":
        return cls(
            name=settings.APP_NAME,
            creator=settings.APP_CREATOR,
            version=settings.APP_VERSION,
            domain=settings.APP_DOMAIN,
            description=settings.APP_DESCRIPTION,
            purpose=settings.APP_PURPOSE,
            supported_languages=settings.SUPPORTED_LANGUAGES,
            available_capabilities=settings.AVAILABLE_CAPABILITIES,
            supported_providers=settings.SUPPORTED_PROVIDERS,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "creator": self.creator,
            "version": self.version,
            "domain": self.domain,
            "description": self.description,
            "purpose": self.purpose,
            "supported_languages": self.supported_languages,
            "available_capabilities": self.available_capabilities,
            "supported_providers": self.supported_providers,
        }


# Global identity instance
app_identity = ApplicationIdentity.from_settings()


def get_identity_response(model_metadata: Optional[ModelMetadata] = None) -> str:
    """Generate the standard identity response."""
    identity = app_identity
    
    provider_info = "unknown"
    model_info = "unknown"
    capabilities = ", ".join(identity.available_capabilities)
    
    if model_metadata:
        provider_info = model_metadata.provider
        model_info = model_metadata.model_display_name or model_metadata.model_id
        if model_metadata.fallback_status:
            provider_info += f" (fallback from {model_metadata.fallback_from})"
    
    return f"""Hello! I am {identity.name}, an intelligent AI assistant developed by {identity.creator}.

I am designed to help with conversations, research, programming, document analysis, problem-solving, productivity and intelligent task execution.

My creator is {identity.creator}, who developed {identity.name} to provide an intelligent and reliable personal AI experience.

I use {provider_info} and the currently selected model is {model_info}.

Here are my technical details:

- Application: {identity.name}
- Creator: {identity.creator}
- Application version: {identity.version}
- AI provider: {provider_info}
- Selected model: {model_info}
- Model availability: {model_metadata.request_status if model_metadata else 'unknown'}
- Available capabilities: {capabilities}

I can help you with a wide range of everyday and technical tasks."""


def get_model_info_response(model_metadata: ModelMetadata) -> str:
    """Generate response for model-specific questions."""
    lines = [
        f"**Current Model Information:**",
        f"- Provider: {model_metadata.provider}",
        f"- Model: {model_metadata.model_display_name or model_metadata.model_id}",
        f"- Selection: {model_metadata.selection_source}",
    ]
    
    if model_metadata.requested_model and model_metadata.requested_model != model_metadata.actual_resolved_model:
        lines.append(f"- Requested: {model_metadata.requested_model}")
        lines.append(f"- Actual (resolved): {model_metadata.actual_resolved_model}")
    
    if model_metadata.fallback_status:
        lines.append(f"- ⚠️ Fallback: Yes (from {model_metadata.fallback_from})")
    
    lines.append(f"- Status: {model_metadata.request_status}")
    
    if model_metadata.verified_capabilities:
        lines.append(f"- Verified Capabilities: {', '.join(model_metadata.verified_capabilities)}")
    
    return "\n".join(lines)


# Provider model display names
MODEL_DISPLAY_NAMES = {
    "gemini": {
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
    },
    "groq": {
        "llama-3.3-70b-versatile": "Llama 3.3 70B Versatile",
        "llama-3.1-70b-versatile": "Llama 3.1 70B Versatile",
        "mixtral-8x7b-32768": "Mixtral 8x7B",
        "gemma2-9b-it": "Gemma 2 9B",
    },
    "openrouter": {
        "openai/gpt-4o-mini": "GPT-4o Mini (via OpenRouter)",
        "openai/gpt-4o": "GPT-4o (via OpenRouter)",
        "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet (via OpenRouter)",
        "meta-llama/llama-3.3-70b-instruct": "Llama 3.3 70B Instruct (via OpenRouter)",
    },
    "bedrock": {
        "anthropic.claude-3-5-sonnet-20241022-v2:0": "Claude 3.5 Sonnet v2 (Bedrock)",
        "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku (Bedrock)",
    },
    "openai": {
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-4o": "GPT-4o",
        "gpt-4-turbo": "GPT-4 Turbo",
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
        "claude-3-haiku-20240307": "Claude 3 Haiku",
    },
    "perplexity": {
        "llama-3.1-sonar-large-128k-online": "Sonar Large Online",
        "llama-3.1-sonar-small-128k-online": "Sonar Small Online",
    },
}


def get_model_display_name(provider: str, model_id: str) -> str:
    """Get human-readable model display name."""
    return MODEL_DISPLAY_NAMES.get(provider, {}).get(model_id, model_id)


def build_model_metadata(
    provider: str,
    model_id: str,
    selection_source: str = "auto",
    requested_model: Optional[str] = None,
    fallback_from: Optional[str] = None,
    request_status: str = "success",
) -> ModelMetadata:
    """Build model metadata from provider response info."""
    actual_resolved = model_id
    fallback_status = fallback_from is not None
    
    # Determine verified capabilities based on provider/model
    capabilities = ["chat", "streaming"]
    if provider in ("gemini", "openrouter", "openai", "anthropic", "bedrock"):
        capabilities.append("vision")
    if provider in ("gemini", "groq", "openrouter", "openai", "anthropic", "bedrock", "perplexity"):
        capabilities.append("tools")
    if provider in ("gemini", "openrouter", "openai", "anthropic", "bedrock"):
        capabilities.append("json_mode")
    
    return ModelMetadata(
        provider=provider,
        model_id=model_id,
        model_display_name=get_model_display_name(provider, model_id),
        selection_source=selection_source,
        requested_model=requested_model,
        actual_resolved_model=actual_resolved,
        fallback_status=fallback_status,
        fallback_from=fallback_from,
        request_status=request_status,
        verified_capabilities=capabilities,
    )