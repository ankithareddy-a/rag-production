"""
ingest.py  —  POST /ingest/text  |  POST /ingest/file

Two ingestion endpoints:
  /ingest/text  → accepts raw JSON with text + source name
  /ingest/file  → accepts multipart file upload (pdf, txt, docx, md)

Both run the full ingestion pipeline:
  load → chunk → embed → store in Redis
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form

from api.models import IngestTextRequest, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])


def _run_pipeline(app_state, documents: list[dict], source: str) -> int:
    """
    Shared ingestion logic: chunk → embed → store.
    Returns number of chunks stored.
    """
    chunker = app_state.chunker
    embedder = app_state.embedder
    vector_store = app_state.vector_store

    # 1. Chunk documents
    chunks = chunker.chunk(documents)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced no chunks")

    # 2. Embed all chunks in one batch (efficient)
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed(texts)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb

    # 3. Store in Redis vector index
    stored = vector_store.load(chunks)
    logger.info(f"Ingested {stored} chunks for source: {source}")
    return stored


@router.post("/text", response_model=IngestResponse)
async def ingest_text(req: IngestTextRequest, request: Request):
    """
    Ingest raw text.

    Example:
        POST /ingest/text
        {"text": "Machine learning is...", "source": "ml-intro"}
    """
    loader = request.app.state.loader
    documents = loader.load_text(req.text, source=req.source)
    stored = _run_pipeline(request.app.state, documents, req.source)

    return IngestResponse(
        status="success",
        source=req.source,
        chunks_stored=stored,
        message=f"Successfully ingested {stored} chunks from '{req.source}'",
    )


@router.post("/file", response_model=IngestResponse)
async def ingest_file(
    request: Request,
    file: UploadFile = File(..., description="PDF, TXT, DOCX, or MD file"),
):
    """
    Ingest an uploaded file.

    Example (curl):
        curl -X POST http://localhost:8000/ingest/file \\
             -F "file=@my_document.pdf"
    """
    allowed_types = {".pdf", ".txt", ".docx", ".md"}
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_types}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    loader = request.app.state.loader
    try:
        documents = loader.load_bytes(content, filename=file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    stored = _run_pipeline(request.app.state, documents, file.filename)

    return IngestResponse(
        status="success",
        source=file.filename,
        chunks_stored=stored,
        message=f"Successfully ingested {stored} chunks from '{file.filename}'",
    )


@router.delete("/source/{source_name}")
async def delete_source(source_name: str, request: Request):
    """
    Remove all chunks from a specific source document.
    Useful when re-ingesting an updated version of a file.
    """
    request.app.state.vector_store.delete_by_source(source_name)
    return {"status": "deleted", "source": source_name}
