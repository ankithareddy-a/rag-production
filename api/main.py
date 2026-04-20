"""
main.py

FastAPI application entry point.

Lifespan pattern (startup/shutdown):
  - All heavy objects (embedding model, Redis index, LLM client) are created
    ONCE at startup and stored on app.state.
  - Routes access them via request.app.state — no global variables.
  - On shutdown, connections are cleanly closed.

This avoids recreating expensive objects on every request.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routes import ingest, query, health

from ingestion import DocumentLoader, Chunker, Embedder
from retrieval import VectorStore, Retriever
from generation import OllamaLLM, PromptBuilder
from cache import SemanticCache

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all dependencies on startup, clean up on shutdown."""
    logger.info("Starting RAG system...")

    # Document ingestion pipeline
    app.state.loader = DocumentLoader()
    app.state.chunker = Chunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    app.state.embedder = Embedder(model_name=settings.embedding_model)

    # Vector store (Redis)
    app.state.vector_store = VectorStore(
        redis_url=settings.redis_url,
        index_name=settings.vector_index_name,
        prefix=settings.vector_doc_prefix,
        dims=settings.embedding_dims,
    )
    app.state.vector_store.create(overwrite=False)

    # Retriever
    app.state.retriever = Retriever(index=app.state.vector_store.get_index())

    # LLM
    app.state.llm = OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
    )

    # Prompt builder
    app.state.prompt_builder = PromptBuilder()

    # Semantic cache
    app.state.cache = SemanticCache(
        redis_url=settings.redis_url,
        embedder=app.state.embedder,
        threshold=settings.cache_threshold,
    )

    logger.info("RAG system ready! Visit http://localhost:8000/docs")

    yield  # ← application runs here

    logger.info("Shutting down RAG system...")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Production RAG API",
    description=(
        "A production-grade Retrieval-Augmented Generation system "
        "powered by Redis (vector search), Ollama (local LLM), "
        "and sentence-transformers (local embeddings)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Streamlit UI (localhost:8501) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(ingest.router, prefix="/ingest")
app.include_router(query.router,  prefix="/query")
app.include_router(health.router, prefix="/health")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Production RAG API",
        "docs": "/docs",
        "health": "/health",
        "ingest_text": "POST /ingest/text",
        "ingest_file": "POST /ingest/file",
        "query": "POST /query/",
        "stream": "POST /query/stream",
    }
