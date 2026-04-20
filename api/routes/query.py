"""
query.py  —  POST /query/

The main RAG endpoint. Full pipeline:
  1. Check semantic cache  → instant answer if hit
  2. Embed the question
  3. Retrieve top-k similar chunks from Redis
  4. Build prompt with retrieved context
  5. Generate answer via Ollama
  6. Cache the result
  7. Return answer + sources

Also includes a streaming endpoint for real-time token output.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from api.models import QueryRequest, QueryResponse, SourceRef

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request):
    """
    Ask a question. Returns a grounded answer with source citations.

    The answer is based ONLY on documents you've ingested.
    If no relevant context is found, the LLM will say so.
    """
    state = request.app.state
    cache = state.cache
    embedder = state.embedder
    retriever = state.retriever
    llm = state.llm
    prompt_builder = state.prompt_builder

    # ── Step 1: Semantic cache check ────────────────────────────────────────
    cached_answer = cache.check(req.question)
    if cached_answer:
        return QueryResponse(
            answer=cached_answer,
            cached=True,
            sources=[],
            question=req.question,
        )

    # ── Step 2: Embed the question ───────────────────────────────────────────
    query_embedding = embedder.embed_one(req.question)

    # ── Step 3: Retrieve relevant chunks ────────────────────────────────────
    chunks = retriever.retrieve(
        query_embedding=query_embedding,
        top_k=req.top_k,
        source_filter=req.source_filter,
        score_threshold=req.score_threshold,
    )

    if not chunks:
        no_ctx = prompt_builder.no_context_response()
        return QueryResponse(
            answer=no_ctx,
            cached=False,
            sources=[],
            question=req.question,
        )

    # ── Step 4: Build prompt ─────────────────────────────────────────────────
    prompt = prompt_builder.build_rag_prompt(chunks, req.question)
    logger.debug(f"Prompt length: {len(prompt)} chars, chunks: {len(chunks)}")

    # ── Step 5: Generate answer ──────────────────────────────────────────────
    try:
        answer = await llm.generate(prompt)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # ── Step 6: Cache the result ─────────────────────────────────────────────
    cache.store(req.question, answer)

    # ── Step 7: Build response ───────────────────────────────────────────────
    # Deduplicate sources and attach their scores
    seen = {}
    for c in chunks:
        src = c["source"]
        if src not in seen or c["score"] > seen[src]:
            seen[src] = c["score"]

    sources = [SourceRef(source=s, score=sc) for s, sc in seen.items()]
    sources.sort(key=lambda x: x.score, reverse=True)

    return QueryResponse(
        answer=answer,
        cached=False,
        sources=sources,
        question=req.question,
    )


@router.post("/stream")
async def query_stream(req: QueryRequest, request: Request):
    """
    Streaming version of the query endpoint.
    Returns Server-Sent Events (SSE) with tokens as they are generated.

    Use this endpoint for the chat UI to show a "typing" effect.

    Example (curl):
        curl -X POST http://localhost:8000/query/stream \\
             -H "Content-Type: application/json" \\
             -d '{"question": "What is RAG?"}' \\
             --no-buffer
    """
    state = request.app.state

    query_embedding = state.embedder.embed_one(req.question)
    chunks = state.retriever.retrieve(query_embedding, top_k=req.top_k)

    if not chunks:
        async def no_ctx_stream():
            yield state.prompt_builder.no_context_response()
        return StreamingResponse(no_ctx_stream(), media_type="text/plain")

    prompt = state.prompt_builder.build_rag_prompt(chunks, req.question)

    async def token_stream():
        async for token in state.llm.stream(prompt):
            yield token

    return StreamingResponse(token_stream(), media_type="text/plain")
