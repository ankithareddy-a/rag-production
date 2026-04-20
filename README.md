# Production RAG System

A production-grade Retrieval-Augmented Generation (RAG) system built entirely with open-source tools. Runs 100% locally — no API keys, no cloud services.

## Tech Stack

| Component | Tool | Purpose |
|---|---|---|
| LLM | Ollama (Llama 3) | Local language model |
| Embeddings | sentence-transformers | Local vector embeddings (no API key) |
| Vector DB | Redis Stack + RedisVL | Vector storage & similarity search |
| API | FastAPI | Async REST API |
| UI | Streamlit | Chat interface |
| Containers | Docker Compose | Local deployment |

## Architecture

```
User Question
     │
     ▼
[Semantic Cache] ──HIT──► Return instantly
     │ MISS
     ▼
[Embedder] → 384-dim vector
     │
     ▼
[Redis HNSW Vector Search] → top-5 relevant chunks
     │
     ▼
[Prompt Builder] → context + question
     │
     ▼
[Ollama / Llama 3] → generates grounded answer
     │
     ▼
[Cache Store] → save for future queries
     │
     ▼
Response + Sources
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Redis + Ollama)
- Python 3.11+

## Setup & Run

### 1. Install Python dependencies

```bash
cd rag-production
pip install -r requirements.txt
```

### 2. Start Redis Stack and Ollama

```bash
docker compose up -d
```

This starts:
- **Redis Stack** on port `6379` (vector store)
- **RedisInsight** on port `8001` (Redis UI — open `http://localhost:8001`)
- **Ollama** on port `11434` (local LLM server)

### 3. Pull the LLM model (one-time, ~4GB download)

```bash
docker exec -it rag-ollama ollama pull llama3
```

> **Alternatives if llama3 is too large:**
> - `ollama pull llama3.2:1b` (1B params, very fast, less accurate)
> - `ollama pull mistral` (7B, good balance)
> - `ollama pull phi3` (3.8B, fast and capable)
>
> Then update `OLLAMA_MODEL` in `.env`.

### 4. Ingest sample documents

```bash
python scripts/ingest_sample.py
```

This loads 3 sample documents about Machine Learning, Redis, and RAG itself.

### 5. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

### 6. Start the Chat UI (new terminal)

```bash
streamlit run ui/app.py
```

- Chat UI: `http://localhost:8501`

## Usage

### Via the Chat UI

1. Open `http://localhost:8501`
2. Upload a PDF or paste text in the sidebar
3. Type your question in the chat box
4. The answer will stream in with source citations

### Via the API directly

**Ingest a document:**
```bash
curl -X POST http://localhost:8000/ingest/file \
     -F "file=@my_document.pdf"
```

**Ask a question:**
```bash
curl -X POST http://localhost:8000/query/ \
     -H "Content-Type: application/json" \
     -d '{"question": "What is machine learning?"}'
```

**Stream a response:**
```bash
curl -X POST http://localhost:8000/query/stream \
     -H "Content-Type: application/json" \
     -d '{"question": "Explain RAG in simple terms"}' \
     --no-buffer
```

**Check system health:**
```bash
curl http://localhost:8000/health
```

## Project Structure

```
rag-production/
├── docker-compose.yml         # Redis Stack + Ollama
├── requirements.txt
├── .env                       # Configuration
│
├── ingestion/
│   ├── document_loader.py     # Load PDF, TXT, DOCX, MD
│   ├── chunker.py             # Recursive text splitting
│   └── embedder.py            # sentence-transformers embeddings
│
├── retrieval/
│   ├── vector_store.py        # Redis HNSW vector index
│   └── retriever.py           # Similarity + hybrid search
│
├── generation/
│   ├── llm.py                 # Ollama async wrapper
│   └── prompt.py              # RAG prompt templates
│
├── cache/
│   └── semantic_cache.py      # Redis semantic cache
│
├── api/
│   ├── main.py                # FastAPI app + lifespan
│   ├── config.py              # Settings from .env
│   ├── models.py              # Pydantic request/response models
│   └── routes/
│       ├── ingest.py          # POST /ingest/text, /ingest/file
│       ├── query.py           # POST /query/, /query/stream
│       └── health.py          # GET /health
│
├── scripts/
│   └── ingest_sample.py       # Load sample docs into Redis
│
├── data/
│   └── sample_docs/           # 3 sample .txt documents
│
└── ui/
    └── app.py                 # Streamlit chat interface
```

## Configuration

Edit `.env` to customize:

```env
OLLAMA_MODEL=llama3            # Change the LLM model
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Change the embedding model
TOP_K=5                        # Default number of retrieved chunks
CHUNK_SIZE=512                 # Characters per chunk
CHUNK_OVERLAP=64               # Overlap between chunks
CACHE_THRESHOLD=0.90           # Semantic cache similarity threshold
```

## Monitoring

- **RedisInsight** (`http://localhost:8001`): Browse stored vectors, monitor memory, run commands
- **FastAPI docs** (`http://localhost:8000/docs`): Interactive API explorer
- **Health endpoint** (`http://localhost:8000/health`): Redis + Ollama status, document count

## Stopping

```bash
docker compose down          # Stop containers (keep data)
docker compose down -v       # Stop containers AND delete data
```

## What Makes This Production-Grade

| Feature | Implementation |
|---|---|
| No hallucination | LLM grounded to retrieved context only |
| Fast retrieval | HNSW approximate nearest-neighbor in Redis |
| Cache hits in <10ms | Redis semantic cache avoids redundant LLM calls |
| Async throughout | FastAPI + httpx async |
| Hybrid search | Vector similarity + metadata filter |
| Smart chunking | Recursive splitter preserves paragraph/sentence boundaries |
| Zero API cost | Ollama + sentence-transformers run 100% locally |
| Source citations | Every answer shows which document it came from |
| Health monitoring | `/health` endpoint + RedisInsight |
| Containerized | One `docker compose up -d` to start everything |
