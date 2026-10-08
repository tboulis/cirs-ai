# CIRS-Agent Backend

FastAPI backend for the Critical Infrastructure Resilience Support chatbot.

## Features

- RESTful API with automatic OpenAPI documentation
- Multiple LLM provider support (OpenAI, local models)
- Document upload and processing
- Vector search with semantic similarity
- Conversation management
- Real-time chat functionality

## Setup

### Prerequisites

- Python 3.8+
- pip or conda
- (Optional) OpenAI API key
- (Optional) Hugging Face API key

### Installation

1. Navigate to the backend directory:

    ```bash
      cd backend
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Create an environment file named `.env` (in the `backend` directory) and add the variables shown below:

    ```env
    DATABASE_URL=sqlite:///./cirs_llm.db
    OPENAI_API_KEY=
    HUGGINGFACE_API_KEY=
    DEFAULT_MODEL=gpt-3.5-turbo
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    UPLOAD_DIR=./uploads
    MAX_FILE_SIZE=10485760
    CHROMA_PERSIST_DIR=./chroma_db
    SECRET_KEY=your-secret-key-change-in-production
    ```

5. (Optional) Adjust any paths, keys, or limits as required.

## OpenAI (optional)

  ```env
  OPENAI_API_KEY=your_openai_api_key_here
  ```

## Hugging Face (optional)

  ```env
  HUGGINGFACE_API_KEY=your_huggingface_api_key_here
  ```

## Model Configuration

  ```env
  DEFAULT_MODEL=gpt-3.5-turbo
  EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
  ```

## File Storage

  ```env
  UPLOAD_DIR=./uploads
  MAX_FILE_SIZE=10485760  # 10MB
  ```

## Vector Database

  ```env
  CHROMA_PERSIST_DIR=./chroma_db
  ```

## Security

  ```env
  SECRET_KEY=your-secret-key-change-in-production
  ```

## Running the Server

  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

The API will be available at:

- **API**: <http://localhost:8000>
- **Documentation**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

## API Endpoints

### Health & Status

- `GET /` - API information
- `GET /api/v1/health` - Health check
- `GET /api/v1/models` - Available models

### Chat

- `POST /api/v1/chat` - Send message and get response
- `GET /api/v1/conversations` - List conversations
- `GET /api/v1/conversations/{id}/messages` - Get conversation messages
- `DELETE /api/v1/conversations/{id}` - Delete conversation
- `POST /api/v1/sessions` - Create chat session

### Documents

- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `POST /api/v1/documents/{id}/process` - Process document
- `POST /api/v1/documents/search` - Search documents
- `DELETE /api/v1/documents/{id}` - Delete document

## Architecture

### Core Components

- **FastAPI Application** (`app/main.py`) - Main application entry point
- **Database Models** (`app/models/`) - SQLAlchemy models
- **API Routers** (`app/routers/`) - Endpoint definitions
- **Services** (`app/services/`) - Business logic
- **Schemas** (`app/schemas/`) - Pydantic models for validation

### Services

- **LLMService** - Handles interactions with language models
- **DocumentService** - Processes documents and manages embeddings

### Database

Uses SQLAlchemy with support for:

- SQLite (development)
- PostgreSQL (production)

### Vector DB

ChromaDB for storing and searching document embeddings.

## Development

### Adding New Models

1. Update `LLMService` in `app/services/llm_service.py`
2. Add model configuration in `app/core/config.py`
3. Update the models endpoint in `app/routers/health.py`

### Running Tests (TODO)

```bash
pytest tests/
```

### Database Migrations (TODO)

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Production Deployment

1. Set production environment variables
2. Use PostgreSQL instead of SQLite
3. Configure reverse proxy (nginx)
4. Use process manager (systemd, supervisor)
5. Set up SSL/TLS certificates

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License
