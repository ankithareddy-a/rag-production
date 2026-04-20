"""
retriever.py

Queries the Redis vector index to find the most semantically similar chunks
for a given question embedding.

Two query modes:
  1. Pure vector search     — similarity only
  2. Hybrid search          — similarity + metadata filter (faster, more precise)

Why hybrid search?
  Filtering by source/tag BEFORE the ANN search narrows the candidate set,
  making retrieval faster and results more relevant. Always use it when you
  know the user is asking about a specific document.

Score interpretation:
  Redis returns "vector_distance" for cosine:
    0.0 = identical vectors
    1.0 = completely different
  We convert to a relevance score = 1 - distance (higher = better).
"""

from __future__ import annotations

import logging
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag

logger = logging.getLogger(__name__)

RETURN_FIELDS = ["content", "source", "chunk_id", "chunk_idx"]


class Retriever:
    def __init__(self, index: SearchIndex):
        self.index = index

    def retrieve(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        source_filter: str | None = None,
        score_threshold: float | None = None,
    ) -> list[dict]:
        """
        Find the top_k most similar chunks to the query embedding.

        Args:
            query_embedding:  vector from the embedder (must match index dims)
            top_k:            number of results to return
            source_filter:    if set, restrict search to this source file
            score_threshold:  if set, drop results below this relevance score
                              (0.0–1.0, higher = more relevant)

        Returns:
            List of dicts with keys: content, source, chunk_id, score
        """
        filter_expr = None
        if source_filter:
            filter_expr = Tag("source") == source_filter

        query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=RETURN_FIELDS,
            num_results=top_k,
            filter_expression=filter_expr,
        )

        raw_results = self.index.query(query)

        results = []
        for r in raw_results:
            distance = float(r.get("vector_distance", 1.0))
            relevance = round(1.0 - distance, 4)  # convert distance → relevance

            if score_threshold is not None and relevance < score_threshold:
                logger.debug(f"Dropping low-relevance chunk ({relevance:.3f}): {r['chunk_id']}")
                continue

            results.append({
                "content":  r["content"],
                "source":   r["source"],
                "chunk_id": r["chunk_id"],
                "score":    relevance,
            })

        logger.info(
            f"Retrieved {len(results)} chunks "
            f"(filter={source_filter}, top_k={top_k})"
        )
        return results

    def retrieve_multi_source(
        self,
        query_embedding: list[float],
        sources: list[str],
        top_k_per_source: int = 3,
    ) -> list[dict]:
        """
        Retrieve from multiple sources and merge results.
        Useful when you want to compare answers across documents.
        """
        all_results = []
        for source in sources:
            results = self.retrieve(query_embedding, top_k=top_k_per_source, source_filter=source)
            all_results.extend(results)

        # Sort merged results by relevance score (descending)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results
