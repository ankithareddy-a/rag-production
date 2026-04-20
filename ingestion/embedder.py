"""
embedder.py

Converts text into dense vector embeddings using a local sentence-transformers
model. No API key needed — the model runs entirely on your machine.

Model choice: all-MiniLM-L6-v2
  - 384 dimensions (small = fast)
  - Trained specifically for semantic similarity / retrieval tasks
  - Excellent quality-to-speed ratio on CPU
  - Downloads automatically on first use (~90MB)

Why normalize? Cosine similarity requires unit-length vectors. Normalizing
at embed time means we can use dot product (faster) instead of full cosine.
"""

import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dims = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model ready. Dimensions: {self.dims}")

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed a list of strings.
        
        batch_size=32: processes 32 texts at a time for memory efficiency.
        normalize_embeddings=True: required for cosine similarity in Redis.
        
        Returns list of float lists (JSON-serializable for storage).
        """
        if not texts:
            return []

        # Filter out empty strings to avoid model errors
        texts = [t if t.strip() else " " for t in texts]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,   # unit-length vectors for cosine sim
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
        )
        logger.debug(f"Embedded {len(texts)} texts → shape {embeddings.shape}")
        return embeddings.tolist()

    def embed_one(self, text: str) -> list[float]:
        """Convenience method for embedding a single string."""
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self.dims
