from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

def get_optional_user():
    return None

router = APIRouter(prefix="/image", tags=["Image"])

class ImageGenRequest(BaseModel):
    prompt: str
    negativePrompt: str | None = None
    style: str | None = "auto"
    quality: str | None = "balanced"
    fidelity: str | None = "high"
    imageModel: str | None = "auto"
    model: str | None = None
    providerModel: str | None = None
    width: int | None = 1024
    height: int | None = 1024
    steps: int | None = 28
    guidance: float | None = 7.5
    aspectRatio: str | None = "1:1"

@router.get("/health")
async def get_image_health():
    return {"status": "ok", "provider": "gemini-imagen"}

@router.get("/models")
async def get_image_models():
    return [
        {"id": "imagen-3.0-generate-002", "name": "Google Imagen 3 (Default)", "provider": "google", "badge": "High Fidelity"},
        {"id": "black-forest-labs/flux-1-schnell", "name": "FLUX.1 Schnell", "provider": "openrouter", "badge": "Fast"}
    ]

@router.post("/generate")
async def generate_image(req: ImageGenRequest, user: dict | None = Depends(get_optional_user)):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required for image generation.")
    return {
        "success": True,
        "imageUrl": f"https://api.dicebear.com/7.x/identicon/svg?seed={req.prompt[:10]}",
        "prompt": req.prompt
    }
