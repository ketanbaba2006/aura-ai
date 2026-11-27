from fastapi import APIRouter, Depends
from app.config import settings

def get_optional_user():
    return None

router = APIRouter(prefix="/models", tags=["Models"])

def build_model(model_id: str, name: str, description: str, capabilities: list[str], ctx: int = 128000, available: bool = True, badge: str = "Active") -> dict:
    return {
        "id": model_id,
        "modelId": model_id,
        "name": name,
        "displayName": name,
        "description": description,
        "capabilities": capabilities,
        "contextLength": ctx,
        "available": available,
        "badge": badge,
        "supportsChat": "CHAT" in capabilities,
        "supportsReasoning": "REASONING" in capabilities,
        "supportsVision": "VISION" in capabilities,
        "supportsCoding": "CODING" in capabilities,
        "supportsImage": "IMAGE_GEN" in capabilities,
        "supportsVideo": "VIDEO_GEN" in capabilities
    }

@router.get("")
@router.post("/refresh")
async def get_models(user: dict | None = Depends(get_optional_user)):
    providers_list = [
        {
            "id": "groq",
            "name": "Groq Ultra-Fast (Free Forever)",
            "available": bool(settings.GROQ_API_KEY),
            "badge": "⚡ 800 TPS",
            "models": [
                build_model("qwen/qwen3.8-27b", "Qwen 3.8 27B", "Ultra-fast 27B model for programming, general conversation & analysis", ["CHAT", "REASONING", "CODING"], 131072, badge="Free ⚡"),
                build_model("openai/gpt-oss-120b", "OpenAI GPT-OSS 120B", "Massive 120B open architecture for deep reasoning, logic, and mathematics", ["CHAT", "REASONING"], 131072, badge="120B Flagship")
            ]
        },
        {
            "id": "openrouter",
            "name": "Cloud Intelligence (Free Tier)",
            "available": True,
            "badge": "🌐 CLOUD",
            "models": [
                build_model("nvidia/nemotron-3.5-lightning:free", "Nemotron 3.5 Lightning", "High-speed zero-cost reasoning model with free access", ["CHAT", "REASONING"], 131072, badge="Free ⚡"),
                build_model("cohere/north-mini-code:free", "Cohere North Mini-Code", "Specialized free coding assistant for rapid syntax & debugging", ["CHAT", "CODING"], 65536, badge="Free Code"),
                build_model("google/gemma-4-31b-it:free", "Gemma 4 31B (Free)", "Google open weights multimodal with zero cost", ["CHAT", "REASONING"], 131072, badge="Google Free")
            ]
        },
        {
            "id": "omniroute",
            "name": "OmniRoute AI Gateway",
            "available": bool(getattr(settings, "OMNIROUTE_API_KEY", getattr(settings, "OPENROUTER_API_KEY", None))),
            "badge": "🚀 ROUTER",
            "models": [
                build_model("auto/best-chat", "Omni Best Chat", "Auto-routed optimal conversational model", ["CHAT", "REASONING"], 131072, badge="Auto 🎯"),
                build_model("auto/best-coding", "Omni Best Coding", "Auto-routed high-performance programming & logic engine", ["CHAT", "CODING", "REASONING"], 1050000, badge="Code Pro ⚡"),
                build_model("auto/best-fast", "Omni Best Fast", "Auto-routed ultra-low-latency high throughput reasoning", ["CHAT"], 131072, badge="Speed ⚡")
            ]
        },
        {
            "id": "local",
            "name": "Local On-Device Engine (Offline Free)",
            "available": True,
            "badge": "💻 LOCAL",
            "models": [
                build_model("qwen3-vl:4b", "Qwen 3 VL Multimodal", "On-device multimodal vision and document intelligence", ["CHAT", "VISION", "REASONING"], 32768, badge="Multimodal"),
                build_model("llama3.2:1b", "Llama 3.2 1B", "Ultra-compact offline foundation model for basic inquiries", ["CHAT"], 8192, badge="Offline")
            ]
        }
    ]

    total_models = sum(len(p["models"]) for p in providers_list)
    return {
        "success": True,
        "totalProviders": len(providers_list),
        "totalModels": total_models,
        "providers": providers_list
    }
