# CIRS-LLM: Critical Infrastructure Resilience Support Chatbot

An LLM-powered chatbot for critical infrastructure resilience support, built with React frontend and Python backend.

## Project Structure

```bash
cirs-agent/
├── backend/          # Python FastAPI backend
│   ├── app/          # Application code
│   ├── requirements.txt
│   └── README.md
├── frontend/         # React web application
│   ├── src/          # Source code
│   ├── public/       # Static assets
│   ├── package.json
│   └── README.md
└── README.md
```

## Features

- Interactive chat interface for infrastructure resilience queries
- Support for multiple LLM providers (OpenAI GPT, Mistral, LLaMA)
- Document processing and question-answering capabilities
- Modern web interface built with React
- RESTful API backend with FastAPI
- Real-time chat functionality
- RAG (Retrieval-Augmented Generation) with Langchain

## Getting Started

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## Run locally with Docker

### Prerequisites

- Docker Engine 20.10+ and Docker Compose plugin

### 1) Configure environment

Copy the example env and edit values as needed (e.g., `OPENAI_API_KEY`):

```bash
cp backend/env.example backend/.env
```

Then set `SECRET_KEY` in `backend/.env` to a random value of at least 32 characters (the backend refuses to start otherwise), e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`, and configure an LLM provider (`OPENAI_API_KEY` or `OPENAI_COMPAT_BASE_URL`).

### 2) Build and start containers

From the repo root:

```bash
docker compose up -d --build
```

This starts:

- `web`: Nginx serving the React build at `/` and proxying `/api/` to the backend, published on port 9494
- `backend`: FastAPI on port 8000, also published on port 8000 for direct API access and the interactive docs at `/docs`

If a port is taken, change the host side of the mapping in `docker-compose.yml` (e.g. `"9595:80"` for `web`), then re-run the command above. Remove the backend's `ports` entry if the API should only be reachable through Nginx.

### 3) Verify

```bash
curl -I http://localhost:9494/
curl    http://localhost:9494/api/v1/health
```

Open your browser at `http://localhost:9494`. The FastAPI docs are at `http://localhost:8000/docs`.

### 4) Logs and lifecycle

```bash
# Follow logs
docker compose logs -f backend
docker compose logs -f web

# Stop (keep data volumes)
docker compose down

# Stop and remove data volumes (DB, uploads, chroma)
docker compose down -v
```

### Data persistence

The compose file uses named volumes to keep your data across restarts:

- `dbdata`: SQLite database at `/data/cirs_llm.db`
- `uploads`: uploaded documents at `/app/uploads`
- `chroma`: vector store at `/app/chroma_db`

You can switch to host bind mounts by replacing these volumes in `docker-compose.yml` with host paths (e.g., `- ./data/db:/data`).

## Technologies

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: Python, FastAPI, SQLAlchemy
- **LLM Integration**: Hugging Face Transformers, Langchain (RAG), OpenAI API, Mistral, LLaMA, Gemini, Groq, etc.
- **Database**: SQLite (development), PostgreSQL (production)

## Demo Users

Created on startup only when `SEED_DEMO_USERS=true` in `backend/.env` (local development only):

- `lyra_1` / `blue-sky-river`
- `lyra_2` / `green-forest-bird`
- `lyra_3` / `red-sun-mountain`
- `lyra_4` / `yellow-moon-lake`
- `lyra_5` / `purple-star-wind`
