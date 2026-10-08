# CIRS-Agent – Developer Notes

## 1. High-Level Architecture

* **Backend**: Python 3.11, FastAPI, SQLAlchemy, ChromaDB, Sentence-Transformers, OpenAI SDK.
* **Frontend**: React 18 + TypeScript, Tailwind CSS, React-Query, React-Router.
* **Persistence**: SQLite (default) with SQLAlchemy ORM; persistent vector store via ChromaDB.
* **Deployment**: Backend served on port 8000; frontend on port 3000 (CRA / Vite style).

Directory skeleton:

```bash
backend/app/      # FastAPI application
frontend/         # React SPA
uploads/          # User-uploaded documents
chroma_db/        # Persisted vector database files
```

---

## 2. Backend Features (FastAPI)

* **Typed settings**: `app/core/config.py` centralizes all environment variables with Pydantic-Settings.
* **Relational models**: `app/models/models.py` defines `Conversation`, `Message`, `Document`, `DocumentChunk`, `ChatSession`.
* **Database setup**: `app/core/database.py` builds a SQLAlchemy engine & `SessionLocal`; tables auto-create in `main.py`.
* **Health router**: `/api/v1/health` reports DB status, available LLM models, version, etc.; `/api/v1/models` enumerates models.
* **Chat router**:
  * Retrieves or creates conversations.
  * **Domain relevance check**:
    * Loads the same `SentenceTransformer` model used for document embeddings (if available).
    * Encodes the **raw user message**.
    * Computes **cosine similarity** between the two vectors via
      \(\text{sim}(a,b)=\frac{a\cdot b}{\|a\|\,\|b\|}\).
    * Compares the score against `settings.CONVERSATION_RELEVANCE_THRESHOLD` (default **0.3**).
    * If the score is **below** the threshold:
      * Skips LLM invocation.
      * Persists both the user question and a canned assistant reminder (role="system") in the database.
      * Returns the reminder to the frontend so the user is nudged back to the CIRS topic space.
  * **Context retrieval (RAG)** – when `use_context=true`, queries ChromaDB for the top-N similar chunks (default 5) limited by optional `document_ids`, then injects those chunks into the LLM system prompt.
  * Persists user & assistant messages along with timing (`response_time`) and token counts (`tokens_used`).
* **Document router**: Endpoints for uploading, processing (extract → chunk → embed), listing, searching, and deleting documents (with embedding cleanup stub).
* **LLMService**:
  * Supports OpenAI models (`gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo-preview`).
  * Builds a domain-specific system prompt and injects context chunks.
* **DocumentService**: Handles the complete document life-cycle.
  * **Extraction**
    * PDF → `PyPDF2.PdfReader` to iterate pages and concatenate `page.extract_text()` results.
    * DOCX → `python-docx` to read paragraphs.
    * TXT / MD → direct file read with UTF-8 fallback to Latin-1.
  * **Chunking algorithm**
    * Splits raw text into windows of `chunk_size` characters (default **1000**).
    * Attempts to break on **sentence boundaries** (`. ! ?`). If none exist close to the limit, falls back to the last whitespace to avoid word truncation.
    * Uses **overlap** (`chunk_overlap`, default **200**) so each chunk shares context with its neighbors.
  * **Embedding + storage**
    * Each chunk embedding is produced by `SentenceTransformer` then stored in a **persistent ChromaDB collection** (`hnsw:space=cosine`).
    * Embedding IDs follow `doc_{document_id}_chunk_{index}`; metadata contains `document_id`, `chunk_id`, `chunk_index`, and type info.
  * **Semantic search**
    * Encodes the query, performs a vector search (`n_results = limit*2`), converts distances to similarity (1-distance), filters by `similarity_threshold` (default **0.7**) and optional document filter, then returns the top-`limit` chunks.
  * **Cleanup & stats** helpers for embedding deletion and collection statistics.

---

## 3. Frontend Features (React)

* **ChatLayout**: Main shell combining sidebar and `ChatInterface`.
* **ChatInterface**: Real-time chat UI with markdown rendering, code highlighting, auto-scroll, typing indicator, and live metrics (model, tokens, latency). Uses React-Query mutation to call `/chat`.
* **DocumentsPage**: Upload widget with search/filter, process, download, and delete actions that interact with the document API. Displays processing status & chunk count.
* **SettingsPage**: Tabs for model list, database health, API keys (placeholder), and about page. Fetches `/health` & `/models` data.
* **Global styling**: Tailwind CSS plus custom utilities in `index.css` for buttons, cards, messages, and spinners.

---

## 4. Important Behavioral Details

1. **Domain Check (Relevance Filter)**  
   Implemented in `app/routers/chat.py` lines ~30-70. Uses `SentenceTransformer` to ensure user queries relate to the CIRS domain before invoking the LLM.
2. **Context-Aware Answers**  
   When `use_context` flag is set, the backend searches previously uploaded & processed documents and prepends the most similar chunks to the system prompt, enabling retrieval-augmented generation (RAG).
3. **Token / Latency Metrics**  
   The chat endpoint records `tokens_used` and `response_time` per assistant message for easy analytics.
4. **Chunking Strategy**  
   Document text is split on sentence/word boundaries up to `chunk_size` (default 1000 chars) with `chunk_overlap` (default 200) to preserve context continuity.
5. **Vector Store**  
   Chroma’s HNSW w/ cosine similarity, persisted in `./chroma_db`; embeddings are identified by `doc_{document_id}_chunk_{i}`.

---

## 5. API Endpoint Reference (Prefix `/api/v1`)

* `GET /health` – system status.
* `GET /models` – available LLM models.
* `POST /chat` – send chat request (`ChatRequest`).
* `GET /conversations` – list conversations.
* `GET /conversations/{id}/messages` – messages for a conversation.
* `DELETE /conversations/{id}` – soft delete.
* `POST /documents/upload` – multipart upload.
* `POST /documents/{id}/process` – chunk & embed.
* `GET /documents` – list.
* `GET /documents/{id}` – detail.
* `POST /documents/search` – semantic search.
* `DELETE /documents/{id}` – delete file + data.

---

## 6. Environment Variables (excerpt)

* `DATABASE_URL`: SQLAlchemy connection string (default `sqlite:///./cirs_llm.db`).
* `OPENAI_API_KEY`: Enables OpenAI models.
* `EMBEDDING_MODEL`: SentenceTransformer model name (default `all-MiniLM-L6-v2`).
* `CHROMA_PERSIST_DIR`: Vector DB persistence path (default `./chroma_db`).
* `CONVERSATION_RELEVANCE_THRESHOLD`: Domain similarity cut-off (default `0.3`).

---

## 7. Development Notes & Ideas

* **Local model integration**: Replace placeholder `_generate_local_response` with actual inference using `transformers` or `llama.cpp`.
* **Embeddings cleanup**: Implement `DocumentService.delete_document_embeddings` call inside `DELETE /documents/{id}` route.
* **Auth & RBAC**: Currently unauthenticated; consider adding JWT login & role-based access for multi-tenant scenarios.
* **Streaming responses**: Upgrade `/chat` to server-sent events or websockets for token-streaming UX.

---

Happy hacking! 🚀
