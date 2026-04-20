"""
vector_store.py

Sets up and manages the Redis vector index using RedisVL.

Index schema stores each chunk as a Redis JSON document with:
  - content:   the raw text (searchable)
  - source:    filename/origin (filterable as a TAG)
  - chunk_id:  unique identifier (filterable as a TAG)
  - embedding: the vector (HNSW index for fast ANN search)

HNSW settings explained:
  M=16              → each node connects to 16 neighbors in the graph.
                      Higher M = better recall, more memory.
  EF_CONSTRUCTION=200 → candidate pool size during index build.
                        Higher = better index quality, slower build.
  These defaults work well up to ~1M documents. Tune up for larger datasets.
"""

import logging
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema

logger = logging.getLogger(__name__)


def build_schema(index_name: str, prefix: str, dims: int) -> dict:
    """Build the index schema dict. Parameterized so dims match the embedder."""
    return {
        "index": {
            "name": index_name,
            "prefix": prefix,
            "storage_type": "json",
        },
        "fields": [
            {"name": "content",   "type": "text"},
            {"name": "source",    "type": "tag"},
            {"name": "chunk_id",  "type": "tag"},
            {"name": "chunk_idx", "type": "numeric"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "algorithm":       "hnsw",
                    "dims":            dims,
                    "distance_metric": "cosine",
                    "m":               16,
                    "ef_construction": 200,
                    # ef_runtime: candidate pool at query time. Higher = better
                    # recall but slower. Default 10 is fine for most use cases.
                    "ef_runtime":      10,
                },
            },
        ],
    }


class VectorStore:
    def __init__(self, redis_url: str, index_name: str, prefix: str, dims: int):
        self.redis_url = redis_url
        self.index_name = index_name
        self.dims = dims
        schema_dict = build_schema(index_name, prefix, dims)
        schema = IndexSchema.from_dict(schema_dict)
        self.index = SearchIndex(schema)
        self.index.connect(redis_url)

    def create(self, overwrite: bool = False) -> None:
        """
        Create the index in Redis.
        overwrite=False means it won't destroy existing data if the index exists.
        Set overwrite=True only when you need to change the schema.
        """
        self.index.create(overwrite=overwrite)
        logger.info(f"Vector index '{self.index_name}' ready (dims={self.dims})")

    def load(self, chunks: list[dict]) -> int:
        """
        Store a list of chunk dicts into Redis.
        Each chunk must have: content, source, chunk_id, chunk_idx, embedding.
        
        Batch load is far more efficient than loading one at a time.
        Returns the number of documents stored.
        """
        if not chunks:
            return 0

        records = []
        for chunk in chunks:
            records.append({
                "content":   chunk["content"],
                "source":    chunk["source"],
                "chunk_id":  chunk["chunk_id"],
                "chunk_idx": chunk.get("chunk_idx", 0),
                "embedding": chunk["embedding"],
            })

        self.index.load(records, id_field="chunk_id")
        logger.info(f"Stored {len(records)} chunks in Redis")
        return len(records)

    def delete_by_source(self, source: str) -> None:
        """Remove all chunks belonging to a specific source document."""
        from redisvl.query.filter import Tag
        results = self.index.query(
            self._source_filter_query(source)
        )
        keys = [r["id"] for r in results]
        if keys:
            client = self.index.client
            client.delete(*keys)
            logger.info(f"Deleted {len(keys)} chunks for source: {source}")

    def get_index(self) -> SearchIndex:
        return self.index

    def info(self) -> dict:
        """Return index stats — useful for health checks."""
        try:
            return self.index.info()
        except Exception:
            return {}

    def _source_filter_query(self, source: str):
        from redisvl.query import FilterQuery
        from redisvl.query.filter import Tag
        return FilterQuery(
            filter_expression=Tag("source") == source,
            return_fields=["chunk_id"],
            num_results=10000,
        )
