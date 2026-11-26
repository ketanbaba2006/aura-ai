"""
AURA AI Identity API
Endpoints for application identity and model information.
"""

import logging
from fastapi import APIRouter, Depends
from app.core.auth_security import get_current_user
from app.core.identity import app_identity, build_model_metadata, get_identity_response, get_model_info_response
from app.core.model_manager import model_manager, PROVIDERS_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/identity", tags=["Identity"])


@router.get("")
async def get_identity():
    """Get application identity information."""
    # Get current active provider/model info
    active_provider = model_manager.active_provider
    config = PROVIDERS_CONFIG.get(active_provider, {})
    active_model = config.get("models", {}).get("chat", "unknown")
    
    model_meta = build_model_metadata(
        provider=active_provider,
        model_id=active_model,
        selection_source="auto",
    )
    
    return {
        "application": app_identity.to_dict(),
        "current_model": {
            "provider": model_meta.provider,
            "model_id": model_meta.model_id,
            "model_display_name": model_meta.model_display_name,
            "selection_source": model_meta.selection_source,
            "verified_capabilities": model_meta.verified_capabilities,
        },
        "identity_response": get_identity_response(model_meta),
    }


@router.get("/model")
async def get_current_model():
    """Get detailed current model information."""
    active_provider = model_manager.active_provider
    config = PROVIDERS_CONFIG.get(active_provider, {})
    active_model = config.get("models", {}).get("chat", "unknown")
    
    # Get provider status
    provider_status = model_manager.stats["status"].get(active_provider, "unknown")
    latencies = model_manager.stats["latencies"].get(active_provider, [])
    latency = round(latencies[-1], 3) if latencies else 0.0
    
    model_meta = build_model_metadata(
        provider=active_provider,
        model_id=active_model,
        selection_source="auto",
        request_status="active" if provider_status == "active" else provider_status,
    )
    
    return {
        "provider": model_meta.provider,
        "model_id": model_meta.model_id,
        "model_display_name": model_meta.model_display_name,
        "selection_source": model_meta.selection_source,
        "fallback_status": model_meta.fallback_status,
        "fallback_from": model_meta.fallback_from,
        "request_status": model_meta.request_status,
        "latency_seconds": latency,
        "provider_status": provider_status,
        "verified_capabilities": model_meta.verified_capabilities,
        "model_info_response": get_model_info_response(model_meta),
    }


@router.get("/providers")
async def get_provider_status():
    """Get status of all configured providers."""
    stats = model_manager.get_stats()
    
    providers = []
    for provider_name in ["gemini", "groq", "openrouter"]:
        config = PROVIDERS_CONFIG.get(provider_name, {})
        model_id = config.get("models", {}).get("chat", "unknown")
        circuit = stats["circuits"].get(provider_name, {})
        
        providers.append({
            "name": provider_name,
            "model": model_id,
            "model_display_name": circuit.get("model", model_id),
            "status": stats["status"].get(provider_name, "unknown"),
            "state": circuit.get("state", "UNKNOWN"),
            "consecutive_failures": circuit.get("consecutive_failures", 0),
            "quota_exhausted": circuit.get("quota_exhausted", False),
            "cooldown_remaining": circuit.get("cooldown_remaining", 0),
            "remaining_requests": circuit.get("remaining_requests", 0),
            "avg_latency": stats["avg_latencies"].get(provider_name, 0),
            "configured": bool(config.get("key") and config["key"] != f"INSECURE_DEFAULT_{provider_name.upper()}_KEY"),
        })
    
    return {
        "active_provider": stats["active_provider"],
        "providers": providers,
        "failover_chain": [p for p in ["gemini", "groq", "openrouter"] if stats["status"].get(p) == "active"],
    }