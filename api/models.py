"""
models.py

Pydantic models for request/response validation.
FastAPI uses these to:
  - Auto-validate incoming JSON
  - Auto-generate OpenAPI docs at /docs
  - Serialize responses
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Raw text content to ingest")
    source: str = Field(..., min_length=1, description="A name/label for this document")


class IngestResponse(BaseModel):
    status: str
    source: str
    chunks_stored: int
    message: str


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="The question to answer")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    source_filter: str | None = Field(
        default=None, description="Restrict search to this source document"
    )
    score_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Minimum relevance score for retrieved chunks (0=include all)"
    )


class SourceRef(BaseModel):
    source: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    cached: bool
    sources: list[SourceRef]
    question: str


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    redis: str
    ollama: str
    index_docs: int
