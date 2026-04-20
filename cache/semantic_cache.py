"""
semantic_cache.py

Semantic caching sits in front of the LLM to avoid redundant generation.

How it works:
  1. User asks: "What is machine learning?"
     → embed the question → search the cache → MISS → call LLM → cache result
  2. User asks: "Can you explain machine learning?"
     → embed the question → search the cache → HIT (similarity ≈ 0.97) → return cached answer instantly

Why this matters in production:
  - LLM calls are slow (1-10s). Cache hits are <10ms.
  - Saves compute / API costs on repeated or paraphrased questions.
  - threshold=0.90 means questions must be 90%+ semantically similar to reuse.

Built on top of RedisVL's SemanticCache which stores:
  - The original prompt embedding
  - The cached response
  - A TTL (we set 1 hour by default)
"""

from __future__ import annotations

import logging
from redisvl.extensions.llmcache import SemanticCache as RedisVLSemanticCache

logger = logging.getLogger(__name__)


class SemanticCache:
    def __init__(
        self,
        redis_url: str,
        embedder,
        threshold: float = 0.90,
        ttl: int = 3600,
    ):
        """
        Args:
            redis_url:   Redis connection string
            embedder:    Embedder instance (used to vectorize prompts)
            threshold:   cosine similarity threshold (0–1). Higher = stricter matching.
            ttl:         cache entry lifetime in seconds (default: 1 hour)
        """
        self.embedder = embedder
        self.threshold = threshold

        self.cache = RedisVLSemanticCache(
            name="rag_semantic_cache",
            redis_url=redis_url,
            distance_threshold=1.0 - threshold,  # RedisVL uses distance not similarity
            ttl=ttl,
        )
        logger.info(
            f"Semantic cache ready (threshold={threshold}, ttl={ttl}s)"
        )

    def check(self, query: str) -> str | None:
        """
        Look up a query in the cache.
        Returns the cached answer string if found, else None.
        """
        try:
            results = self.cache.check(prompt=query)
            if results:
                logger.info(f"Cache HIT for query: '{query[:60]}...'")
                return results[0]["response"]
            logger.debug(f"Cache MISS for query: '{query[:60]}'")
            return None
        except Exception as e:
            # Never let cache failures block the main pipeline
            logger.warning(f"Cache check failed (non-fatal): {e}")
            return None

    def store(self, query: str, response: str) -> None:
        """Store a query→response pair in the cache."""
        try:
            self.cache.store(prompt=query, response=response)
            logger.debug(f"Cached response for: '{query[:60]}'")
        except Exception as e:
            logger.warning(f"Cache store failed (non-fatal): {e}")

    def clear(self) -> None:
        """Flush all cached entries — useful when reindexing documents."""
        try:
            self.cache.clear()
            logger.info("Semantic cache cleared")
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
