"""
Dynamic capability + provider detection (spec §5, §7).

Order of evidence:
  1. Metadata the gateway itself exposes (modalities, supported endpoints,
     task names, capability arrays, owned_by...).
  2. Structural hints in the model id (namespaces like `google/`, `openai/`).
  3. Nothing → capabilities stay empty and `determined` is False so the UI can
     honestly show "Capability unknown".

No hardcoded model catalogue is used as a source of truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

CHAT = "CHAT"
VISION = "VISION"
IMAGE_GENERATION = "IMAGE_GENERATION"
EMBEDDINGS = "EMBEDDINGS"
AUDIO = "AUDIO"
CODE = "CODE"
REASONING = "REASONING"

ALL_CAPABILITIES = (CHAT, VISION, IMAGE_GENERATION, EMBEDDINGS, AUDIO, CODE, REASONING)

_CAPABILITY_ALIASES = {
    "chat": CHAT,
    "chat_completion": CHAT,
    "chat.completions": CHAT,
    "chat-completion": CHAT,
    "text": CHAT,
    "text-generation": CHAT,
    "text2text-generation": CHAT,
    "completion": CHAT,
    "completions": CHAT,
    "conversational": CHAT,
    "vision": VISION,
    "image": VISION,
    "image-text-to-text": VISION,
    "image-to-text": VISION,
    "multimodal": VISION,
    "visual-question-answering": VISION,
    "image_generation": IMAGE_GENERATION,
    "image-generation": IMAGE_GENERATION,
    "images": IMAGE_GENERATION,
    "images.generations": IMAGE_GENERATION,
    "text-to-image": IMAGE_GENERATION,
    "text_to_image": IMAGE_GENERATION,
    "embedding": EMBEDDINGS,
    "embeddings": EMBEDDINGS,
    "feature-extraction": EMBEDDINGS,
    "sentence-similarity": EMBEDDINGS,
    "audio": AUDIO,
    "audio-generation": AUDIO,
    "automatic-speech-recognition": AUDIO,
    "speech": AUDIO,
    "text-to-speech": AUDIO,
    "transcription": AUDIO,
    "translations": AUDIO,
    "code": CODE,
    "code-generation": CODE,
    "reasoning": REASONING,
    "thinking": REASONING,
}

# Signals inside model ids. Used only as a *secondary* source of evidence.
_ID_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (EMBEDDINGS, re.compile(r"(^|[/\-_.])(embed|embedding|embeddings|bge|gte|e5|text-embedding)", re.I)),
    (AUDIO, re.compile(r"(whisper|tts|speech|voice|audio|transcrib|sonic|wav2vec)", re.I)),
    (IMAGE_GENERATION, re.compile(r"(dall-?e|imagen|stable-?diffusion|sdxl|flux|midjourney|kandinsky|playground-v|image-?gen|text-to-image|gpt-image)", re.I)),
    (VISION, re.compile(r"(vision|-vl\b|vl-|llava|multimodal|omni|-vlm|image-text)", re.I)),
    (CODE, re.compile(r"(code|coder|codestral|starcoder|deepseek-?coder|devstral|qwen.*coder)", re.I)),
    (REASONING, re.compile(r"(^|[/\-_.])(o1|o3|o4|r1|reason|reasoner|thinking|think|qwq)([\-_.]|$)", re.I)),
)

_RERANK = re.compile(r"(rerank|reranker|moderation|guard|safety|classifier)", re.I)

# Model-id namespaces map to the *vendor* of the model, not to the gateway.
_NAMESPACE_VENDORS = {
    "openai": "OpenAI",
    "google": "Google",
    "gemini": "Google",
    "anthropic": "Anthropic",
    "meta": "Meta",
    "meta-llama": "Meta",
    "mistral": "Mistral AI",
    "mistralai": "Mistral AI",
    "nvidia": "NVIDIA",
    "qwen": "Qwen",
    "deepseek": "DeepSeek",
    "deepseek-ai": "DeepSeek",
    "microsoft": "Microsoft",
    "cohere": "Cohere",
    "ai21": "AI21",
    "x-ai": "xAI",
    "xai": "xAI",
    "perplexity": "Perplexity",
    "amazon": "Amazon",
    "stabilityai": "Stability AI",
    "stability-ai": "Stability AI",
    "black-forest-labs": "Black Forest Labs",
    "moonshotai": "Moonshot AI",
    "z-ai": "Z.AI",
    "baidu": "Baidu",
    "ibm": "IBM",
    "writer": "Writer",
    "nousresearch": "Nous Research",
    "huggingface": "Hugging Face",
    "togethercomputer": "Together",
    "bytedance": "ByteDance",
}

# Host → gateway label. Only used when the host *identifies itself*; otherwise
# we fall back to the honest "OpenAI-compatible Gateway" / "Custom Gateway".
_HOST_GATEWAYS = (
    ("openrouter.ai", "OpenRouter"),
    ("api.groq.com", "Groq"),
    ("api.openai.com", "OpenAI"),
    ("generativelanguage.googleapis.com", "Google"),
    ("integrate.api.nvidia.com", "NVIDIA NIM"),
    ("api.nvcf.nvidia.com", "NVIDIA NIM"),
    ("api.bytez.com", "Bytez"),
    ("api.anthropic.com", "Anthropic"),
    ("api.mistral.ai", "Mistral AI"),
    ("api.deepseek.com", "DeepSeek"),
    ("api.together.xyz", "Together AI"),
    ("api.fireworks.ai", "Fireworks AI"),
    ("api.cerebras.ai", "Cerebras"),
    ("api.x.ai", "xAI"),
    ("api.perplexity.ai", "Perplexity"),
    ("api.cohere.ai", "Cohere"),
    ("api.deepinfra.com", "DeepInfra"),
    ("api.hyperbolic.xyz", "Hyperbolic"),
    ("api.sambanova.ai", "SambaNova"),
    ("api.moonshot.cn", "Moonshot AI"),
    ("dashscope.aliyuncs.com", "Alibaba DashScope"),
    ("azure.com", "Azure OpenAI"),
    ("bedrock", "Amazon Bedrock"),
    ("localhost", "Local Gateway"),
    ("ollama", "Ollama"),
    ("lmstudio", "LM Studio"),
)

GENERIC_GATEWAY = "OpenAI-compatible Gateway"
UNKNOWN_GATEWAY = "Custom Gateway"


@dataclass
class CapabilityVerdict:
    capabilities: list[str] = field(default_factory=list)
    determined: bool = False
    source: str = "unknown"          # "gateway-metadata" | "model-id" | "unknown"
    supports_streaming: bool | None = None
    context_length: int | None = None


def _normalize_tokens(value) -> list[str]:
    """Flatten arbitrary metadata into lowercase string tokens."""
    tokens: list[str] = []
    if value is None:
        return tokens
    if isinstance(value, str):
        tokens.append(value.strip().lower())
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.extend(_normalize_tokens(item))
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, bool):
                if item:
                    tokens.append(str(key).strip().lower())
            else:
                tokens.append(str(key).strip().lower())
                tokens.extend(_normalize_tokens(item))
    else:
        tokens.append(str(value).strip().lower())
    return [t for t in tokens if t]


def _map_tokens(tokens: list[str]) -> list[str]:
    found: list[str] = []
    for token in tokens:
        mapped = _CAPABILITY_ALIASES.get(token)
        if mapped and mapped not in found:
            found.append(mapped)
    return found


def detect_capabilities(model: dict) -> CapabilityVerdict:
    """Infer capabilities for a single raw model object from a gateway."""
    verdict = CapabilityVerdict()
    model_id = str(model.get("id") or model.get("name") or "")

    metadata_caps: list[str] = []

    # -- explicit capability / modality / task metadata -------------------
    for key in (
        "capabilities",
        "capability",
        "supported_generation_methods",
        "supported_endpoint_types",
        "supported_endpoints",
        "endpoints",
        "modalities",
        "modality",
        "task",
        "tasks",
        "pipeline_tag",
        "type",
        "model_type",
        "features",
        "supported_features",
        "output_modalities",
        "input_modalities",
    ):
        if key in model:
            metadata_caps.extend(_map_tokens(_normalize_tokens(model.get(key))))

    architecture = model.get("architecture")
    if isinstance(architecture, dict):
        inputs = _normalize_tokens(architecture.get("input_modalities"))
        outputs = _normalize_tokens(architecture.get("output_modalities"))
        if "image" in inputs:
            metadata_caps.append(VISION)
        if "audio" in inputs:
            metadata_caps.append(AUDIO)
        if "image" in outputs:
            metadata_caps.append(IMAGE_GENERATION)
        if "audio" in outputs:
            metadata_caps.append(AUDIO)
        if "text" in outputs:
            metadata_caps.append(CHAT)
        modality = str(architecture.get("modality") or "").lower()
        if "image" in modality.split("->")[0]:
            metadata_caps.append(VISION)
        if "->image" in modality.replace(" ", ""):
            metadata_caps.append(IMAGE_GENERATION)

    supported_params = _normalize_tokens(model.get("supported_parameters"))
    if supported_params:
        metadata_caps.append(CHAT)
        if any("reasoning" in p or "thinking" in p for p in supported_params):
            metadata_caps.append(REASONING)
        if any("stream" in p for p in supported_params):
            verdict.supports_streaming = True

    for key in ("context_length", "context_window", "max_context_length", "max_input_tokens"):
        raw = model.get(key)
        if isinstance(raw, (int, float)) and raw > 0:
            verdict.context_length = int(raw)
            break

    for key in ("supports_streaming", "streaming", "stream"):
        if isinstance(model.get(key), bool):
            verdict.supports_streaming = model[key]
            break

    # Deduplicate while preserving order.
    metadata_caps = list(dict.fromkeys(c for c in metadata_caps if c in ALL_CAPABILITIES))

    if metadata_caps:
        verdict.capabilities = metadata_caps
        verdict.determined = True
        verdict.source = "gateway-metadata"

    # -- id-based hints ---------------------------------------------------
    id_caps: list[str] = []
    if model_id:
        for capability, pattern in _ID_PATTERNS:
            if pattern.search(model_id):
                id_caps.append(capability)

    if id_caps:
        exclusive = {EMBEDDINGS, AUDIO, IMAGE_GENERATION}
        if not verdict.determined:
            caps = list(dict.fromkeys(id_caps))
            # A vision/code/reasoning model is still a chat model; an embeddings,
            # audio or image-generation model is not.
            if not exclusive.intersection(caps):
                caps.insert(0, CHAT)
            verdict.capabilities = list(dict.fromkeys(caps))
            verdict.determined = True
            verdict.source = "model-id"
        else:
            merged = list(verdict.capabilities)
            for cap in id_caps:
                if cap not in merged:
                    # Never *add* an exclusive capability on top of gateway
                    # metadata — that is how image requests reach text models.
                    if cap in exclusive:
                        continue
                    merged.append(cap)
            # If the id clearly marks an embeddings/audio/image model and the
            # gateway only said "chat", trust the id and drop CHAT.
            for cap in id_caps:
                if cap in exclusive and cap not in merged and len(verdict.capabilities) <= 1:
                    merged = [cap]
            verdict.capabilities = merged

    if model_id and _RERANK.search(model_id) and CHAT in verdict.capabilities:
        verdict.capabilities = [c for c in verdict.capabilities if c != CHAT] or [CHAT]

    return verdict


def detect_model_vendor(model: dict, gateway_label: str) -> str:
    """Best-effort vendor for grouping. Falls back to the gateway label."""
    owned_by = str(model.get("owned_by") or model.get("owner") or model.get("organization") or "").strip()
    model_id = str(model.get("id") or model.get("name") or "")

    if "/" in model_id:
        namespace = model_id.split("/", 1)[0].lower()
        vendor = _NAMESPACE_VENDORS.get(namespace)
        if vendor:
            return vendor

    if owned_by and owned_by.lower() not in {"system", "organization_owner", "custom", "user", "-", "n/a"}:
        vendor = _NAMESPACE_VENDORS.get(owned_by.lower())
        return vendor or owned_by

    lowered = model_id.lower()
    for namespace, vendor in _NAMESPACE_VENDORS.items():
        if lowered.startswith(namespace + "-") or lowered.startswith(namespace + "."):
            return vendor
    if lowered.startswith(("gpt-", "o1", "o3", "o4", "chatgpt", "davinci", "dall-e", "whisper", "tts-")):
        return "OpenAI"
    if lowered.startswith("gemini") or lowered.startswith("imagen"):
        return "Google"
    if lowered.startswith("claude"):
        return "Anthropic"
    if lowered.startswith("llama"):
        return "Meta"
    if lowered.startswith("grok"):
        return "xAI"

    return gateway_label or UNKNOWN_GATEWAY


def detect_gateway_label(
    base_url: str,
    *,
    discovery_succeeded: bool,
    server_header: str | None = None,
    user_label: str | None = None,
) -> str:
    """Identify the gateway itself — never guess a provider without evidence."""
    if user_label and user_label.strip():
        return user_label.strip()

    host = (urlsplit(base_url).hostname or "").lower()
    for needle, label in _HOST_GATEWAYS:
        if needle in host:
            return label

    if server_header:
        header = server_header.lower()
        for needle, label in _HOST_GATEWAYS:
            if needle.split(".")[0] in header:
                return label
        for known in ("ollama", "vllm", "llama.cpp", "litellm", "tgi", "lmstudio"):
            if known in header:
                return known.upper() if known in ("tgi", "vllm") else known.title()

    return GENERIC_GATEWAY if discovery_succeeded else UNKNOWN_GATEWAY
