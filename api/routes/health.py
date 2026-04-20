"""
health.py  —  GET /health

Health check endpoint. Used by:
  - Docker health checks
  - Load balancers
  - Monitoring systems (Prometheus, etc.)

Returns status of each dependency: Redis, Ollama, vector index.
"""

from fastapi import APIRouter, Request
from api.models import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/", response_model=HealthResponse)
async def health(request: Request):
    state = request.app.state

    # Check Redis
    redis_status = "ok"
    index_docs = 0
    try:
        info = state.vector_store.info()
        index_docs = int(info.get("num_docs", 0))
    except Exception as e:
        redis_status = f"error: {e}"

    # Check Ollama
    ollama_status = "ok" if await state.llm.health_check() else "unavailable"

    overall = "healthy" if redis_status == "ok" and ollama_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        redis=redis_status,
        ollama=ollama_status,
        index_docs=index_docs,
    )
