import datetime
from typing import List, Dict, Tuple, Optional
import asyncio
from app.core.config import settings
from openai import OpenAI
from dataclasses import dataclass
from typing import Any, Union
import tiktoken
import httpx

@dataclass
class ContextChunk:
    text: str
    title: str = ""
    section: str = ""
    page: str = ""
    alias: str = ""   # e.g., "NIS2", "ISO22301:2019"

def _count_tokens(messages, model="gpt-4o-mini"):
    # pick a default you actually use
    enc = tiktoken.encoding_for_model(model) if model in tiktoken.list_encoding_names() else tiktoken.get_encoding("cl100k_base")
    total = 0
    for m in messages:
        total += 4  # message overhead (heuristic for chat models)
        total += len(enc.encode(m.get("content", "")))
    return total

def _trim_history_by_tokens(history, model, max_tokens_budget):
    kept = []
    for msg in reversed(history or []):
        candidate = [msg] + kept
        if _count_tokens(candidate, model) <= max_tokens_budget:
            kept = candidate
        else:
            break
    return kept
class LLMService:
    def __init__(self):
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            # Initialize client using new OpenAI SDK interface (>=1.0)
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        context_chunks: List[str] = None,
        model: str = "gpt-3.5-turbo",
        provider: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Tuple[str, Optional[int]]:
        """
        Generate a response using the specified LLM model
        """
        try:
            # Resolve default model if not explicitly provided or blank
            if not model:
                model = self.get_default_model()
            # Prefer explicit OpenAI-compatible hints from request
            if provider == "openai_compatible" and (api_base or settings.OPENAI_COMPAT_BASE_URL):
                return await self._generate_openai_response(
                    message, conversation_history, context_chunks,
                    model, temperature, max_tokens, strict_mode=True,
                    enforce_structure=False, api_base=api_base or settings.OPENAI_COMPAT_BASE_URL, api_key=api_key or settings.OPENAI_COMPAT_API_KEY
                )
            # If an OpenAI-compatible base is configured globally, use it by default for non-OpenAI models
            if settings.OPENAI_COMPAT_BASE_URL and not model.startswith("gpt-"):
                return await self._generate_openai_response(
                    message, conversation_history, context_chunks,
                    model, temperature, max_tokens, strict_mode=True,
                    enforce_structure=False, api_base=settings.OPENAI_COMPAT_BASE_URL, api_key=settings.OPENAI_COMPAT_API_KEY or settings.OPENAI_API_KEY
                )
            if model.startswith("gpt-"):
                return await self._generate_openai_response(
                    message, conversation_history, context_chunks, 
                    model, temperature, max_tokens
                )
            else:
                raise ValueError(f"Unsupported model: {model}")
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

    async def _generate_openai_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        context_chunks: List[Union[ContextChunk, Dict[str, Any], str]] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 800,
        strict_mode: bool = True,
        enforce_structure: bool = False,   # flip this to use Structured Outputs
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:

        if not (self.openai_client or api_key):
            raise Exception("OpenAI API key not configured")

        system_prompt = self._build_system_prompt(
            strict_mode=strict_mode,
            context_chunks=context_chunks,
        )

        # Token-aware history trim (keep ~2k tokens for history as an example)
        history_budget = 2000
        recent_history = _trim_history_by_tokens(conversation_history or [], model, history_budget)

        # Compose a single user message with Context + Question (best grounding)
        context_block = ""
        if context_chunks:
            context_block = "Context:\n" + "\n\n".join(
                f"[{i+1}] " + (c.text if isinstance(c, ContextChunk) else (c.get('text', c) if isinstance(c, dict) else str(c)))
                for i, c in enumerate(context_chunks)
            ) + "\n\n"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent_history)
        messages.append({"role": "user", "content": f"{context_block}Question:\n{message}"})

        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Optional: enforce the 6-section structure with structured outputs (JSON)
        # See "Structured outputs" docs for details.  [oai_citation:4‡OpenAI Platform](https://platform.openai.com/docs/guides/structured-outputs?utm_source=chatgpt.com)
        if enforce_structure:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "ci_rag_answer",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "key_points": {"type": "array", "items": {"type": "string"}},
                            "citations": {"type": "array", "items": {"type": "string"}},
                            "assumptions_limits": {"type": "string"},
                            "next_steps": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "string", "enum": ["High","Medium","Low"]}
                        },
                        "required": ["answer","key_points","citations","confidence"],
                        "additionalProperties": False
                    }
                }
            }

        try:
            # If custom base/api provided, construct a transient OpenAI client
            if api_base or api_key:
                from openai import OpenAI as OpenAIClient
                client = OpenAIClient(api_key=api_key or settings.OPENAI_API_KEY, base_url=api_base or None)
                response = await asyncio.to_thread(client.chat.completions.create, **kwargs)
            else:
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create, **kwargs
                )
            content = response.choices[0].message.content
            tokens_used = getattr(response, "usage", None).total_tokens if getattr(response, "usage", None) else None
            return content, tokens_used
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


    # ------------------------------------------------------------------
    # LangChain adapter – returns a ChatModel ready for vector-RAG chains
    # ------------------------------------------------------------------
    def as_langchain_llm(self, *, model_name: Optional[str] = None, provider: Optional[str] = None, api_base: Optional[str] = None, api_key: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """Return a LangChain-compatible chat model depending on *model_name*.

        Supported:
        • OpenAI Chat models  → `langchain_openai.ChatOpenAI`
        • HuggingFace Inference Hub → `langchain_community.chat_models.ChatHuggingFace`
        • Local GGUF / llama.cpp models  → `langchain_community.llms.LlamaCpp`

        If *model_name* is None the default from settings is used. *temperature* and
        *max_tokens* default to settings.TEMPERATURE and no output limit.
        """

        temperature = settings.TEMPERATURE if temperature is None else temperature

        selected = model_name or self.get_default_model()
        # Fallback: if an OpenAI key is present but no model specified, use a safe default
        if not selected and getattr(settings, "OPENAI_API_KEY", None):
            selected = "gpt-4o-mini"

        # --- OpenAI ------------------------------------------------------
        # Use OpenAI-compatible server if requested or globally configured
        if (provider == "openai_compatible" and (api_base or settings.OPENAI_COMPAT_BASE_URL)) or (
            settings.OPENAI_COMPAT_BASE_URL and not selected.startswith("gpt-")
        ):
            from langchain_openai import ChatOpenAI  # type: ignore

            return ChatOpenAI(
                model=selected,
                api_key=api_key or settings.OPENAI_COMPAT_API_KEY or settings.OPENAI_API_KEY,
                base_url=api_base or settings.OPENAI_COMPAT_BASE_URL,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        if selected.startswith("gpt-") and settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI  # type: ignore

            return ChatOpenAI(
                model=selected,
                api_key=settings.OPENAI_API_KEY,
                base_url=None,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def get_default_model(self) -> str:
        """Resolve the runtime default model.

        Preference:
        1) If no OpenAI API key and OPENAI_COMPAT_BASE_URL configured, use first LM Studio model
        2) Else if OPENAI_COMPAT_BASE_URL configured, still prefer its first model
        3) Else fall back to settings.DEFAULT_MODEL (may be empty)
        """
        if (not getattr(settings, "OPENAI_API_KEY", None)) and getattr(settings, "OPENAI_COMPAT_BASE_URL", None):
            try:
                base = settings.OPENAI_COMPAT_BASE_URL.rstrip("/") + "/models"
                # Use sync httpx within thread to avoid blocking event loop in non-async contexts
                def _fetch():
                    return httpx.get(base, timeout=3.0)
                resp = asyncio.run(asyncio.to_thread(_fetch)) if not asyncio.get_event_loop().is_running() else None
                if resp is None:
                    # We're already in an event loop
                    async def _afetch():
                        async with httpx.AsyncClient(timeout=3.0) as client:
                            return await client.get(base)
                    resp = asyncio.get_event_loop().run_until_complete(_afetch())  # best-effort
                if resp is not None and resp.status_code == 200:
                    data = resp.json()
                    first = (data.get("data") or [{}])[0].get("id")
                    if first:
                        return first
            except Exception:
                pass
        if getattr(settings, "OPENAI_COMPAT_BASE_URL", None):
            try:
                base = settings.OPENAI_COMPAT_BASE_URL.rstrip("/") + "/models"
                def _fetch2():
                    return httpx.get(base, timeout=3.0)
                resp2 = asyncio.run(asyncio.to_thread(_fetch2)) if not asyncio.get_event_loop().is_running() else None
                if resp2 is None:
                    async def _afetch2():
                        async with httpx.AsyncClient(timeout=3.0) as client:
                            return await client.get(base)
                    resp2 = asyncio.get_event_loop().run_until_complete(_afetch2())
                if resp2 is not None and resp2.status_code == 200:
                    data = resp2.json()
                    first = (data.get("data") or [{}])[0].get("id")
                    if first:
                        return first
            except Exception:
                pass
        return settings.DEFAULT_MODEL

    def _build_system_prompt(
        self,
        *,
        strict_mode: bool = True,
        org_name: str = "Example CI Office",
        jurisdiction: str = "EU/Greece",
        date_today: str = None,
        citation_style: str = "inline",  # or "list"
        context_chunks: Optional[List[Union["ContextChunk", Dict[str, Any], str]]] = None,
    ) -> str:
        # single source of truth for “today”
        date_today = date_today or datetime.date.today().isoformat()

        base = f"""You are {org_name}’s retrieval-augmented assistant for critical infrastructure resilience, focused on {jurisdiction}.
        Primary objective: Answer only when supported by retrieved context; cite sources precisely; state limits when evidence is thin.

        Document priority (ties/conflicts):
        1) Law/Directive/Regulation
        2) Official standards (ISO/IEC, IEC 62443)
        3) Authoritative guidance (ENISA, NIST, national CSIRTs/regulators)
        4) Organization policy/procedure ({org_name})
        5) Third-party commentary

        Citation format:
        - Use bracketed inline citations. Examples: [NIS2 Art. 21], [ISO22301:2019 §8.4.2, p.22], [NIST800-34r1 §3.2], [IEC62443-3-3 SR 5.2], [ORG §Policy-12]
        - Never fabricate citations or URLs; every factual claim must trace to provided Context.

        Alias map (extend as needed):
        - {org_name} internal policies → "ORG" (use policy IDs/sections where available)
        - NIS2 → "NIS2"
        - ENISA guidance → "ENISA-[short_title]"
        - ISO 22301:2019 → "ISO22301:2019"
        - ISO/IEC 27001:2022 → "ISO27001:2022"; ISO/IEC 27002:2022 → "ISO27002:2022"
        - NIST SP 800-34 Rev.1 → "NIST800-34r1"; NIST SP 800-61 Rev.2 → "NIST800-61r2"
        - NIST SP 800-82 → "NIST800-82"
        - IEC 62443-3-3 → "IEC62443-3-3"

        Guardrails:
        - Safety first: do not provide instructions that enable exploitation or disruption of infrastructure. If asked, refuse and offer high-level risk awareness.
        - Decision support only; not operational control. Summaries are not legal advice to {org_name}; consult {org_name}’s legal counsel for interpretation.
        - Protect sensitive/PII; anonymize whenever possible.
        - If evidence is missing or conflicting, say “insufficient evidence,” explain what’s missing, and suggest targeted retrieval.

        Retrieval-grounding:
        - Treat provided Context as authoritative. Prefer newer versions and higher-priority sources (with {org_name} policies above third-party content).
        - {"Use Context only." if strict_mode else 'If you add generally accepted background, label it "Background (no citation)" and avoid contradictions.'}

        Output (use this structure every time):
        1) Answer (2–6 sentences)
        2) Key Points (3–7 bullets)
        3) Citations ({citation_style} style)
        4) Assumptions & Limits
        5) Next Steps / What to Retrieve (2–4 items)
        6) Confidence (High/Medium/Low)

        Refusal (for harmful requests):
        “Cannot help with that. The request could facilitate harm to critical infrastructure. I can provide high-level risk awareness and relevant policy references instead. For escalation, contact your {org_name} security lead.”

        Conventions: ISO dates; expand acronyms on first use; quote sparingly; avoid chain-of-thought.

        Today’s date: {date_today}.
        """.format(citation_style)

        # Optional snippet guideline + numbered block
        if context_chunks:
            guideline = (
                "\nYou will be given numbered snippets. When you use a snippet, cite it by alias/anchor if present; "
                "otherwise use [n]. After the answer, include a **Sources:** list mapping [n] → title/section/page.\n"
            )

            # Normalize chunk inputs (string/dict/dataclass)
            def _norm(c):
                from dataclasses import is_dataclass
                if isinstance(c, str):
                    return dict(text=c, title="", section="", page="", alias="")
                if isinstance(c, dict):
                    return {
                        "text": c.get("text", ""),
                        "title": c.get("title", ""),
                        "section": c.get("section", ""),
                        "page": c.get("page", ""),
                        "alias": c.get("alias", ""),
                    }
                if is_dataclass(c):
                    return {
                        "text": getattr(c, "text", ""),
                        "title": getattr(c, "title", ""),
                        "section": getattr(c, "section", ""),
                        "page": getattr(c, "page", ""),
                        "alias": getattr(c, "alias", ""),
                    }
                return {"text": str(c), "title": "", "section": "", "page": "", "alias": ""}

            chunks = [_norm(c) for c in context_chunks]
            lines = []
            for i, ch in enumerate(chunks, 1):
                tag = f"[{ch['alias']}]" if ch.get("alias") else f"[{i}]"
                meta = " — ".join(
                    [x for x in [ch.get("title"), ch.get("section"), f"p.{ch.get('page')}" if ch.get("page") else ""] if x]
                )
                header = f"{tag} {meta}".strip()
                body = ch.get("text", "")
                lines.append(f"{header}\n{body}".strip())

            return base + guideline + "\nSnippets:\n" + "\n\n".join(lines)

        return base

    async def get_available_models(self) -> List[Dict[str, str]]:
        models = []
        if self.openai_client:
            try:
                # list all, keep the chat-capable ones (simple heuristic)
                data = await asyncio.to_thread(self.openai_client.models.list)
                for m in data.data:
                    mid = getattr(m, "id", "")
                    if any(k in mid for k in ["gpt-", "o", "mini"]):  # tweak filter as you like
                        models.append({"name": mid, "provider": "openai", "status": "available"})
            except Exception:
                pass

        return models

    async def validate_model(self, model_name: str) -> bool:
        """
        Validate if a model is available
        """
        available_models = await self.get_available_models()
        return any(model["name"] == model_name for model in available_models) 