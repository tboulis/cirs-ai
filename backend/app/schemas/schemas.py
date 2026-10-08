from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# -------------------- Auth Schemas --------------------

class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Chat Schemas
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[int] = None
    model: Optional[str] = Field(default="gpt-3.5-turbo", description="LLM model to use")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4000)
    use_context: Optional[bool] = Field(default=True, description="Use document context")
    document_ids: Optional[List[int]] = Field(default=[], description="Specific documents to use as context")
    provider: Optional[str] = Field(default=None, description="LLM provider: openai, openai_compatible, huggingface, local")
    api_base: Optional[str] = Field(default=None, description="Custom OpenAI-compatible base URL (e.g., http://host:1234/v1)")
    api_key: Optional[str] = Field(default=None, description="Override API key for this request")

class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response")
    conversation_id: int
    model_used: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    context_used: Optional[bool] = False
    sources: Optional[List[Dict[str, Any]]] = []
    rag_fallback: Optional[bool] = Field(default=False, description="RAG was requested but failed; the answer was generated without retrieval")

    model_config = {"protected_namespaces": ()}

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    message_count: int

class MessageResponse(BaseModel):
    id: int
    content: str
    role: str
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    created_at: datetime
    sources: Optional[List[Dict[str, Any]]] = None

    model_config = {"protected_namespaces": ()}

# Document Schemas
class DocumentUpload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None

class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    uploaded_at: datetime
    processed: bool
    processed_at: Optional[datetime] = None
    chunk_count: int
    title: Optional[str] = None
    description: Optional[str] = None

class DocumentProcessRequest(BaseModel):
    document_id: int
    chunk_size: Optional[int] = Field(default=1000, ge=100, le=5000)
    chunk_overlap: Optional[int] = Field(default=200, ge=0, le=1000)
    
class DocumentSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(default=5, ge=1, le=20)
    similarity_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    document_ids: Optional[List[int]] = Field(default=[], description="Specific documents to search")

class DocumentSearchResult(BaseModel):
    document_id: int
    document_title: str
    chunk_content: str
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = {}

# Model Configuration Schemas
class ModelConfig(BaseModel):
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Model provider (openai, huggingface, local)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)

class ModelListResponse(BaseModel):
    models: List[Dict[str, Any]]
    default_model: str

# Health Check Schema
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database_status: str
    models_available: List[str]

# Error Response Schema
class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime
    
# Session Schema
class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    is_active: bool
    conversation_count: int 