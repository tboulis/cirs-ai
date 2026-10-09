from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.rag_service import RagService
from app.routers import chat, documents, health, auth
from app.core.database import engine, SessionLocal
from app.models import models
from app.core.config import settings

# JWTs are signed with SECRET_KEY: refuse to start with a missing, placeholder or short value
_PLACEHOLDER_SECRETS = {"", "secret_key", "changeme", "secret", "your-secret-key", "your-secret-key-here"}
if settings.SECRET_KEY in _PLACEHOLDER_SECRETS or len(settings.SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY must be a random value of at least 32 characters, e.g. "
        "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
from sqlalchemy import text
import bcrypt

# Load environment variables explicitly from backend/.env so it works cross-platform
try:
    here = os.path.dirname(__file__)
    env_path = os.path.abspath(os.path.join(here, "..", ".env"))
    load_dotenv(env_path)
except Exception:
    # Fallback to default search if explicit path fails
    load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="CIRS-Agent API",
    description="Critical Infrastructure Resilience Support - Chatbot API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])

# ---------------------------------------------------------------------------
# Lifespan events – initialise heavy singleton services once at startup
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """Load heavy ML models once and attach to app.state for dependency use."""
    app.state.doc_service = DocumentService()
    app.state.llm_service = LLMService()

    # Provider-agnostic RAG (works with OpenAI, HF or local models)
    app.state.rag_service = RagService(
        chroma_client=app.state.doc_service.chroma_client,
        llm_service=app.state.llm_service,
    )

    # Ensure messages.sources and user scoping columns exist (simple DDL for SQLite/Postgres)
    try:
        with engine.connect() as conn:
            # SQLite: add column if not exists (no IF NOT EXISTS for ADD COLUMN in SQLite, so try-catch)
            conn.execute(text("ALTER TABLE messages ADD COLUMN sources TEXT"))
    except Exception:
        # Column likely exists; ignore
        pass

    # Add user_id columns if missing
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER"))
    except Exception:
        pass
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN user_id INTEGER"))
    except Exception:
        pass

    # Seed demo users (lyra_1..lyra_5) with simple dash-joined passwords, only when enabled
    if settings.SEED_DEMO_USERS:
        try:
            from app.models.models import User  # local import to avoid circulars at import time

            def hash_password(password: str) -> str:
                salt = bcrypt.gensalt(rounds=12)
                return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
            default_users = [
                ("lyra_1", "blue-sky-river"),
                ("lyra_2", "green-forest-bird"),
                ("lyra_3", "red-sun-mountain"),
                ("lyra_4", "yellow-moon-lake"),
                ("lyra_5", "purple-star-wind"),
            ]

            db = SessionLocal()
            try:
                for username, password in default_users:
                    existing = db.query(User).filter(User.username == username).first()
                    if not existing:
                        user = User(
                            username=username,
                            hashed_password=hash_password(password),
                            is_active=True,
                        )
                        db.add(user)
                db.commit()
            finally:
                db.close()
        except Exception:
            # Never block startup because of seeding issues
            pass


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources if needed (placeholder for future)."""
    # If underlying libraries expose close() / atexit we would call them here.
    pass

@app.get("/")
async def root():
    return {
        "message": "CIRS-Agent API", 
        "description": "Critical Infrastructure Resilience Support Chatbot",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal server error: {str(exc)}"}
    )