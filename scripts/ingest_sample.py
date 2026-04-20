"""
ingest_sample.py

Loads all sample documents from data/sample_docs/ into the Redis vector index.
Run this once after `docker compose up` to populate the knowledge base.

Usage:
    python scripts/ingest_sample.py

What it does:
  1. Connects to Redis (must be running via docker compose)
  2. Creates the vector index if it doesn't exist
  3. Loads all .txt files from data/sample_docs/
  4. Chunks, embeds, and stores them

After running this, you can query the API or UI right away.
"""

import sys
import logging
from pathlib import Path

# Make sure the project root is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import settings
from ingestion import DocumentLoader, Chunker, Embedder
from retrieval import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"

    logger.info("=" * 60)
    logger.info("RAG Sample Ingestion Script")
    logger.info("=" * 60)

    # ── Initialize components ────────────────────────────────────────────────
    logger.info("Loading embedding model (first run downloads ~90MB)...")
    loader = DocumentLoader()
    chunker = Chunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    embedder = Embedder(model_name=settings.embedding_model)

    logger.info("Connecting to Redis...")
    vector_store = VectorStore(
        redis_url=settings.redis_url,
        index_name=settings.vector_index_name,
        prefix=settings.vector_doc_prefix,
        dims=embedder.dimension,
    )
    vector_store.create(overwrite=False)

    # ── Load documents ───────────────────────────────────────────────────────
    logger.info(f"Loading documents from: {sample_dir}")
    documents = loader.load_directory(str(sample_dir))

    if not documents:
        logger.error("No documents found! Check that data/sample_docs/ has files.")
        sys.exit(1)

    logger.info(f"Loaded {len(documents)} document(s)")

    # ── Chunk ────────────────────────────────────────────────────────────────
    chunks = chunker.chunk(documents)
    logger.info(f"Created {len(chunks)} chunks")

    # ── Embed ────────────────────────────────────────────────────────────────
    logger.info("Generating embeddings (this may take a moment on first run)...")
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed(texts)

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb

    # ── Store ─────────────────────────────────────────────────────────────────
    stored = vector_store.load(chunks)

    logger.info("=" * 60)
    logger.info(f"SUCCESS: Stored {stored} chunks in Redis")
    logger.info("")
    logger.info("Now you can:")
    logger.info("  1. Start the API:  uvicorn api.main:app --reload")
    logger.info("  2. Start the UI:   streamlit run ui/app.py")
    logger.info("  3. API docs:       http://localhost:8000/docs")
    logger.info("  4. Redis Insight:  http://localhost:8001")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
