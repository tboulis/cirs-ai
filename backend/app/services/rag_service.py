from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains import create_retrieval_chain

from app.core.config import settings
from app.services.llm_service import LLMService


def _to_langchain_messages(history: List[Tuple[str, str]] | None) -> List[BaseMessage]:
    """Convert your [(role, content)] history to LangChain BaseMessage list."""
    if not history:
        return []
    result: List[BaseMessage] = []
    for role, content in history:
        if role == "user":
            result.append(HumanMessage(content=content))
        else:
            # treat anything not "user" as assistant
            result.append(AIMessage(content=content))
    return result


class RagService:
    """History-aware RAG over an existing Chroma collection.
    Instantiated once at startup and reused via `app.state.rag_service`.
    """

    def __init__(self, *, chroma_client, llm_service: LLMService):
        # --- Embeddings: reuse the already-loaded SentenceTransformer from DocumentService if available ---
        # This prevents loading the same model twice (reduces memory/OOM risk).
        def _build_embedding_fn():
            try:
                # Lazy import to avoid circulars
                from app.main import app  # type: ignore
                doc_svc = getattr(app.state, "doc_service", None)
                st_model = getattr(doc_svc, "embedding_model", None) if doc_svc else None

                if st_model is not None:
                    class _STEmbeddings:
                        def __init__(self, model):
                            self.model = model
                        def embed_documents(self, texts: list[str]) -> list[list[float]]:
                            # batch encode for efficiency
                            import numpy as _np
                            vecs = self.model.encode(texts)
                            return vecs.tolist() if hasattr(vecs, "tolist") else [list(map(float, v)) for v in vecs]
                        def embed_query(self, text: str) -> list[float]:
                            vec = self.model.encode([text])[0]
                            return vec.tolist() if hasattr(vec, "tolist") else list(map(float, vec))
                    return _STEmbeddings(st_model)
            except Exception:
                pass

            # Fallback: construct a fresh HF embedding (may load model once here)
            embedding_model_name = (
                getattr(settings, "EMBEDDING_MODEL", None)
                or "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            )
            return HuggingFaceEmbeddings(model_name=embedding_model_name)

        self.embedding_fn = _build_embedding_fn()

        # --- Vector store (langchain-chroma package, not deprecated community class) ---
        self.vector_store = Chroma(
            client=chroma_client,
            collection_name="documents",
            embedding_function=self.embedding_fn,
        )

        # --- Retriever (use score threshold to reduce junk) ---
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 5, "score_threshold": 0.35},
        )

        # Keep reference to LLM service for dynamic model switching
        self.llm_service = llm_service
        self.current_model_name: Optional[str] = getattr(settings, "DEFAULT_MODEL", None)
        self.current_provider: Optional[str] = None
        self.current_api_base: Optional[str] = None
        self.current_api_key: Optional[str] = None
        self.current_temperature: Optional[float] = None
        self.current_max_tokens: Optional[int] = None

        # --- LLM from your service (provider-agnostic) ---
        # Resolve default if missing
        if not self.current_model_name:
            try:
                self.current_model_name = self.llm_service.get_default_model()
            except Exception:
                self.current_model_name = getattr(settings, "DEFAULT_MODEL", None)
        self.llm = self.llm_service.as_langchain_llm(model_name=self.current_model_name)
        if self.llm is None:
            raise RuntimeError(
                (
                    "No chat model configured. Set one of the following in backend .env: "
                    "(1) OPENAI_API_KEY and DEFAULT_MODEL='gpt-*' for OpenAI, or "
                    "(2) OPENAI_COMPAT_BASE_URL (e.g., http://127.0.0.1:1234/v1) and DEFAULT_MODEL to a model "
                    "exposed by that server (optionally OPENAI_COMPAT_API_KEY)."
                )
            )

        # --- Question rewriter for history-aware retrieval (no `qa_prompt` anywhere) ---
        self.condense_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system",
                 "You are a helpful assistant for Critical Infrastructure Resilience (EU/Greece). "
                 "Rewrite the user's latest question into a standalone search query using the chat history for context. "
                 "Keep entities/abbreviations and language (e.g., Greek) as in the user message. "
                 "Be concise; remove chit-chat."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, self.condense_q_prompt
        )

        # --- Answer synthesizer over retrieved docs ---
        # This prompt is used by create_stuff_documents_chain and MUST contain {context} and {input}
        self.answer_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a retrieval-augmented assistant for critical infrastructure resilience. "
                        "Use only the provided context to answer. If evidence is insufficient or conflicting, say so and request the exact document/section needed. "
                        "Do NOT invent citations. Be concise and practical. "
                        "If the user asks for harmful actions (e.g., system exploitation), refuse."
                        "\n\n"
                        "Context:\n{context}"
                    ),
                ),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        self.combine_docs_chain = create_stuff_documents_chain(
            self.llm, self.answer_prompt
        )

        # Final RAG chain = history-aware retriever → stuff combine chain
        self.chain = create_retrieval_chain(
            self.history_aware_retriever, self.combine_docs_chain
        )

    def _rebuild_for_model(self, model_name: Optional[str], provider: Optional[str] = None, api_base: Optional[str] = None, api_key: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> None:
        """Rebuild LLM and dependent chains if the model/provider/base changes."""
        self.llm = self.llm_service.as_langchain_llm(model_name=model_name, provider=provider, api_base=api_base, api_key=api_key, temperature=temperature, max_tokens=max_tokens)
        self.history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, self.condense_q_prompt
        )
        self.combine_docs_chain = create_stuff_documents_chain(self.llm, self.answer_prompt)
        self.chain = create_retrieval_chain(self.history_aware_retriever, self.combine_docs_chain)

    async def run(
        self, *, question: str, chat_history: List[Tuple[str, str]] | None = None, model_name: Optional[str] = None, provider: Optional[str] = None, api_base: Optional[str] = None, api_key: Optional[str] = None, user_id: Optional[int] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Return `(answer, sources)` where sources are ready for your API schema."""
        if (
            ((model_name or self.current_model_name) and (model_name or self.current_model_name) != self.current_model_name)
            or (provider != self.current_provider)
            or (api_base != self.current_api_base)
            or (api_key and api_key != self.current_api_key)
            or (temperature != self.current_temperature)
            or (max_tokens != self.current_max_tokens)
        ):
            self._rebuild_for_model(model_name or self.current_model_name, provider, api_base, api_key, temperature, max_tokens)
            self.current_model_name = model_name or self.current_model_name
            self.current_provider = provider
            self.current_api_base = api_base
            self.current_api_key = api_key or self.current_api_key
            self.current_temperature = temperature
            self.current_max_tokens = max_tokens
        lc_history = _to_langchain_messages(chat_history)
        # Filter retrieval by user if provided
        if user_id is not None:
            self.retriever.search_kwargs = {
                **self.retriever.search_kwargs,
                "filter": {"user_id": user_id},
            }
        result = await self.chain.ainvoke({"input": question, "chat_history": lc_history})

        answer: str = result.get("answer", "")
        source_docs: List[Document] = result.get("context", [])  # from create_retrieval_chain

        # Prepare your source payload (best-effort keys; depends on your ingest metadata)
        formatted_sources: List[Dict[str, Any]] = []
        for i, doc in enumerate(source_docs, start=1):
            md = doc.metadata or {}
            formatted_sources.append(
                {
                    "id": i,
                    "document_id": md.get("document_id"),
                    "document_title": md.get("document_title") or md.get("source") or md.get("file_name"),
                    "chunk_index": md.get("chunk_index"),
                    # Chroma may return either 'score' or 'relevance_score' (or distance)
                    "similarity_score": md.get("score")
                    or md.get("relevance_score")
                    or md.get("distance"),
                }
            )

        return answer, formatted_sources

    # ------------------------ Indexing Helpers ---------------------------
    async def upsert_chunks(
        self,
        *,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> List[str]:
        """Embed and upsert the provided chunks into Chroma. Returns stored IDs."""
        return self.vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    async def delete_by_document_id(self, *, document_id: int) -> None:
        """Delete all chunks in Chroma that belong to a document."""
        self.vector_store.delete(where={"document_id": document_id})