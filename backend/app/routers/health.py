from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.schemas.schemas import HealthResponse
from app.core.config import settings
import httpx
from app.services.llm_service import LLMService
from sqlalchemy import text

router = APIRouter()


def _curate_openai(models: list[dict]) -> list[dict]:
    """Keep general-purpose chat models; drop audio/realtime/search/tts/image/legacy/date-stamped variants."""
    blacklist = {
        "audio", "realtime", "search", "transcribe", "tts", "image",
        "codex", "instruct", "nano", "deep-research", "preview", "latest",
        # legacy/date-stamped markers we'll avoid in names
        "0613", "1106", "0125", "16k",
    }
    whitelist_prefixes = ("gpt-4o", "gpt-4.1", "gpt-5")
    allowed_exact = {"gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"}

    def is_ok(name: str) -> bool:
        n = name.lower()
        if any(k in n for k in blacklist):
            return False
        if name in allowed_exact:
            return True
        return n.startswith(whitelist_prefixes)

    # Deduplicate by base alias, prefer canonical (undated) variants
    seen = set()
    curated: list[dict] = []
    for m in models:
        name = m.get("name", "")
        if not name or not is_ok(name):
            continue
        base = name.split("-20")[0]  # collapse dated variants (e.g., -2024-..)
        if base in seen:
            continue
        seen.add(base)
        curated.append({
            "name": name,
            "provider": m.get("provider", "openai"),
            "status": m.get("status", "available"),
            "description": m.get("description", ""),
        })

    prefer = {"gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"}
    curated_sorted = sorted(curated, key=lambda x: (x["name"] not in prefer, x["name"]))
    return curated_sorted


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to monitor API status
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Dynamically fetch available models from provider(s)
    available_models: list[str] = []
    try:
        llm_service = LLMService()
        provider_models = await llm_service.get_available_models()
        openai_models = [m for m in provider_models if m.get("provider") == "openai"]
        curated = _curate_openai(openai_models)
        available_models.extend([m["name"] for m in curated])
    except Exception:
        # Non-fatal: fall back to minimal set
        available_models.extend(["gpt-4o", "gpt-4o-mini"])  # indicative only

    # Always include local/open-source placeholders
    for local in ["sentence-transformers"]:
        if local not in available_models:
            available_models.append(local)

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.now(),
        version="1.0.0",
        database_status=db_status,
        models_available=available_models
    )


@router.get("/models")
async def get_available_models():
    """
    Get list of available LLM models.
    Provider-driven when possible; otherwise returns a safe fallback set.
    """
    models: list[dict] = []

    # Try provider-driven discovery via LLMService (OpenAI account)
    try:
        llm_service = LLMService()
        provider_models = await llm_service.get_available_models()
        openai_models = [m for m in provider_models if m.get("provider") == "openai"]
        curated = _curate_openai(openai_models)
        models.extend(curated)
    except Exception:
        # Fallback to a minimal modern static set
        models.extend([
            {"name": "gpt-4o", "provider": "openai", "description": "Multimodal GPT-4o", "status": "available"},
            {"name": "gpt-4o-mini", "provider": "openai", "description": "Fast GPT-4o mini", "status": "available"},
        ])

    # Merge LM Studio (OpenAI-compatible) models if configured
    if settings.OPENAI_COMPAT_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.OPENAI_COMPAT_BASE_URL.rstrip('/') + "/models")
                resp.raise_for_status()
                data = resp.json()
                for m in data.get("data", []):
                    mid = m.get("id") or m.get("name")
                    if not mid:
                        continue
                    entry = {
                        "name": mid,
                        "provider": "openai_compatible",
                        "description": "LM Studio (discovered)",
                        "status": "available",
                    }
                    if all(x.get("name") != entry["name"] for x in models):
                        models.append(entry)
        except Exception:
            # Non-fatal if LM Studio not reachable
            pass

    # Always include local/open-source entries (discovery handled elsewhere)
    # Default selection policy:
    # - If no OpenAI API key but LM Studio is configured, prefer LM Studio models
    # - Otherwise, pick the first available model
    if not settings.OPENAI_API_KEY and settings.OPENAI_COMPAT_BASE_URL:
        lm_models = [m for m in models if m.get("provider") == "openai_compatible"]
        if lm_models:
            default_model = lm_models[0]["name"]
        else:
            default_model = models[0]["name"] if models else settings.DEFAULT_MODEL
    else:
        default_model = models[0]["name"] if models else settings.DEFAULT_MODEL

    return {
        "models": models,
        "default_model": default_model
    }