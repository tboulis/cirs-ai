from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Tuple
import time
import uuid
from datetime import datetime
import numpy as np

from app.core.database import get_db
from app.models.models import Conversation, Message, ChatSession, User
from app.schemas.schemas import (
    ChatRequest, ChatResponse, ConversationResponse,
    MessageResponse, SessionResponse
)
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.core.config import settings
from app.dependencies import get_current_user

router = APIRouter()

RAG_FALLBACK_NOTICE = (
    "[Η ανάκτηση από τη βάση γνώσης απέτυχε: η απάντηση δεν βασίζεται σε έγγραφα και δεν έχει πηγές. "
    "Retrieval failed: this answer is not based on the knowledge base and has no sources.]\n\n"
)


def _domain_similarity(embedding_model, text: str) -> float:
    """Max cosine similarity between *text* and the "||"-separated domain descriptions."""
    descriptions = [d.strip() for d in settings.DOMAIN_DESCRIPTION.split("||") if d.strip()]
    domain_embs = embedding_model.encode(descriptions)
    text_emb = embedding_model.encode([text])[0]
    return max(
        float(np.dot(d, text_emb) / (np.linalg.norm(d) * np.linalg.norm(text_emb)))
        for d in domain_embs
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the LLM and get a response.
    """
    start_time = time.time()

    try:
        # Initialize services (reuse singletons from app.state to avoid heavy reloads)
        llm_service = getattr(request.app.state, "llm_service", None) or LLMService()
        doc_service = getattr(request.app.state, "doc_service", None) or DocumentService()

        # Get or create conversation
        if chat_req.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == chat_req.conversation_id,
                Conversation.user_id == current_user.id,
                Conversation.is_active == True
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # -------- Domain relevance check (for ongoing conversation) --------
            try:
                if getattr(doc_service, "embedding_model", None):
                    recent_msgs = db.query(Message).filter(
                        Message.conversation_id == conversation.id
                    ).order_by(Message.created_at.desc()).limit(5).all()

                    aggregated_text = " ".join([m.content for m in reversed(recent_msgs)]) + " " + chat_req.message

                    similarity = _domain_similarity(doc_service.embedding_model, aggregated_text)

                    if similarity < settings.CONVERSATION_RELEVANCE_THRESHOLD:
                        generic_response = (
                            "I'm specialized in Critical Infrastructure Resilience Support "
                            "(cybersecurity, risk assessment, business continuity, incident response, "
                            "regulatory compliance, physical security, network security, etc.). "
                            "Please ask questions related to that domain so I can assist you effectively."
                        )

                        # Store user message and assistant reminder
                        db.add(Message(conversation_id=conversation.id, content=chat_req.message, role="user"))
                        db.add(Message(conversation_id=conversation.id, content=generic_response,
                                       role="assistant", model_used="system"))
                        conversation.updated_at = datetime.now()
                        db.commit()

                        response_time = time.time() - start_time
                        return ChatResponse(
                            message=generic_response,
                            conversation_id=conversation.id,
                            model_used="system",
                            tokens_used=None,
                            response_time=response_time,
                            context_used=False,
                            sources=[],
                        )
            except HTTPException:
                raise
            except Exception as e:
                # Best-effort; don't block chat on relevance errors
                print(f"Domain relevance check failed: {e}")

        else:
            # New conversation
            conversation = Conversation(
                title=chat_req.message[:50] + "..." if len(chat_req.message) > 50 else chat_req.message
            )
            conversation.user_id = current_user.id
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

            # -------- Domain relevance check (first message) --------
            try:
                if getattr(doc_service, "embedding_model", None):
                    similarity = _domain_similarity(doc_service.embedding_model, chat_req.message)

                    if similarity < settings.CONVERSATION_RELEVANCE_THRESHOLD:
                        generic_response = (
                            "I'm specialized in Critical Infrastructure Resilience Support "
                            "(cybersecurity, risk assessment, business continuity, incident response, "
                            "regulatory compliance, physical security, network security, etc.). "
                            "Please ask questions related to that domain so I can assist you effectively."
                        )

                        db.add(Message(conversation_id=conversation.id, content=chat_req.message, role="user"))
                        db.add(Message(conversation_id=conversation.id, content=generic_response,
                                       role="assistant", model_used="system"))
                        conversation.updated_at = datetime.now()
                        db.commit()

                        response_time = time.time() - start_time
                        return ChatResponse(
                            message=generic_response,
                            conversation_id=conversation.id,
                            model_used="system",
                            tokens_used=None,
                            response_time=response_time,
                            context_used=False,
                            sources=[],
                        )
            except HTTPException:
                raise
            except Exception as e:
                print(f"Domain relevance check failed: {e}")

        # Conversation history (last 20), read before saving the current message so it holds
        # earlier turns only: both flows receive the current message separately
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).limit(20).all()

        conversation_history = [{"role": m.role, "content": m.content} for m in reversed(messages)]

        # Save user message
        db.add(Message(conversation_id=conversation.id, content=chat_req.message, role="user"))
        db.commit()

        # ------------------------- RAG path -------------------------
        sources: List[dict] = []
        tokens_used = None
        rag_fallback = False
        response_content: str

        if chat_req.use_context:
            try:
                rag_service = getattr(request.app.state, "rag_service", None)
                if rag_service is None:
                    raise RuntimeError("RAG service not initialized on app.state")

                # langchain chains expect history as list[tuple[str, str]]
                lc_history: List[Tuple[str, str]] = [(m["role"], m["content"]) for m in conversation_history]

                response_content, sources = await rag_service.run(
                    question=chat_req.message,
                    chat_history=lc_history,
                    model_name=chat_req.model,
                    provider=chat_req.provider,
                    api_base=chat_req.api_base,
                    api_key=chat_req.api_key,
                    user_id=current_user.id,
                    temperature=chat_req.temperature,
                    max_tokens=chat_req.max_tokens,
                )
            except Exception as e:
                # Fallback to plain completion, flagged so the answer is never mistaken for a grounded one
                print(f"RAG failed: {e}")
                rag_fallback = True
                response_content, tokens_used = await llm_service.generate_response(
                    message=chat_req.message,
                    conversation_history=conversation_history,
                    context_chunks=[],  # no snippets in this fallback path
                    model=chat_req.model,
                    provider=chat_req.provider,
                    api_base=chat_req.api_base,
                    api_key=chat_req.api_key,
                    temperature=chat_req.temperature,
                    max_tokens=chat_req.max_tokens,
                )
                response_content = RAG_FALLBACK_NOTICE + response_content
        else:
            response_content, tokens_used = await llm_service.generate_response(
                message=chat_req.message,
                conversation_history=conversation_history,
                context_chunks=[],
                model=chat_req.model,
                provider=chat_req.provider,
                api_base=chat_req.api_base,
                api_key=chat_req.api_key,
                temperature=chat_req.temperature,
                max_tokens=chat_req.max_tokens,
            )

        response_time = time.time() - start_time

        # Save assistant message (persist sources if present)
        import json as _json
        db.add(Message(
            conversation_id=conversation.id,
            content=response_content,
            role="assistant",
            model_used=chat_req.model,
            tokens_used=tokens_used,
            response_time=response_time,
            sources=_json.dumps(sources) if sources else None,
        ))

        conversation.updated_at = datetime.now()
        db.commit()

        return ChatResponse(
            message=response_content,
            conversation_id=conversation.id,
            model_used=chat_req.model,
            tokens_used=tokens_used,
            response_time=response_time,
            context_used=bool(sources),
            sources=sources,
            rag_fallback=rag_fallback,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

    result = []
    for conv in conversations:
        message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            is_active=conv.is_active,
            message_count=message_count
        ))
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()

    import json as _json
    result: list[MessageResponse] = []
    for msg in messages:
        parsed_sources = None
        if getattr(msg, "sources", None):
            try:
                parsed_sources = _json.loads(msg.sources)
            except Exception:
                parsed_sources = None
        result.append(MessageResponse(
            id=msg.id,
            content=msg.content,
            role=msg.role,
            model_used=msg.model_used,
            tokens_used=msg.tokens_used,
            response_time=msg.response_time,
            created_at=msg.created_at,
            sources=parsed_sources,
        ))
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.is_active = False
    db.commit()
    return {"message": "Conversation deleted successfully"}


@router.post("/sessions", response_model=SessionResponse)
async def create_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    session = ChatSession(session_id=session_id, created_at=datetime.now(), last_activity=datetime.now())
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        last_activity=session.last_activity,
        is_active=session.is_active,
        conversation_count=0
    )