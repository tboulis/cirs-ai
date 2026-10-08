FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for scientific stack (numpy, torch wheels work without build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

# Default paths (overridable by env)
ENV DATABASE_URL=sqlite:////data/cirs_llm.db \
    UPLOAD_DIR=/app/uploads \
    CHROMA_PERSIST_DIR=/app/chroma_db

EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]


