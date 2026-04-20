"""
chunker.py

Splits large documents into overlapping chunks that fit within embedding
model token limits while preserving as much semantic meaning as possible.

Why chunking matters:
  - Embedding models have a max input length (~512 tokens for MiniLM).
  - Smaller chunks = more precise retrieval (less noise).
  - Overlap ensures context isn't lost at chunk boundaries.

Strategy: RecursiveCharacterTextSplitter tries to split on natural
boundaries in order: paragraph → sentence → word → character.
"""

import logging
import hashlib
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class Chunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        """
        chunk_size:    target character count per chunk (~512 chars ≈ 100-150 tokens)
        chunk_overlap: how many chars the next chunk re-uses from the previous one
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Try splitting on paragraphs first, then sentences, then words
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            length_function=len,
        )

    def chunk(self, documents: list[dict]) -> list[dict]:
        """
        Takes a list of document dicts and returns a flat list of chunk dicts.

        Input:  [{"content": "...", "source": "file.pdf", "metadata": {...}}]
        Output: [{"content": "...", "source": "file.pdf", "chunk_id": "abc123:0", ...}]
        """
        chunks = []
        for doc in documents:
            raw_chunks = self.splitter.split_text(doc["content"])
            for i, text in enumerate(raw_chunks):
                if not text.strip():
                    continue
                # Deterministic chunk_id = hash(source + position)
                chunk_id = self._make_id(doc["source"], i)
                chunks.append({
                    "content":  text,
                    "source":   doc["source"],
                    "chunk_id": chunk_id,
                    "chunk_idx": i,
                    "metadata": doc.get("metadata", {}),
                })

        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks

    def _make_id(self, source: str, idx: int) -> str:
        """Generate a stable, unique ID for each chunk."""
        raw = f"{source}:{idx}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
