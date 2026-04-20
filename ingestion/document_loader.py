"""
document_loader.py

Loads documents from various sources:
  - Plain text (.txt)
  - PDF files (.pdf)
  - Word documents (.docx)
  - Raw strings (for API uploads)

Each loader returns a list of dicts with keys:
  { "content": str, "source": str, "metadata": dict }
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Unified document loader supporting txt, pdf, and docx formats."""

    def load_text(self, text: str, source: str = "manual_input") -> list[dict]:
        """Load a raw string directly — useful for API text uploads."""
        return [{"content": text.strip(), "source": source, "metadata": {}}]

    def load_file(self, file_path: str) -> list[dict]:
        """
        Auto-detect file type by extension and load accordingly.
        Raises ValueError for unsupported types.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        loaders = {
            ".txt":  self._load_txt,
            ".pdf":  self._load_pdf,
            ".docx": self._load_docx,
            ".md":   self._load_txt,
        }

        loader_fn = loaders.get(ext)
        if not loader_fn:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {list(loaders)}")

        logger.info(f"Loading {ext} file: {path.name}")
        return loader_fn(file_path, source=path.name)

    def load_directory(self, dir_path: str) -> list[dict]:
        """Load all supported files from a directory recursively."""
        docs = []
        for root, _, files in os.walk(dir_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    docs.extend(self.load_file(fpath))
                except ValueError:
                    logger.debug(f"Skipping unsupported file: {fname}")
                except Exception as e:
                    logger.warning(f"Failed to load {fname}: {e}")
        logger.info(f"Loaded {len(docs)} documents from {dir_path}")
        return docs

    def load_bytes(self, data: bytes, filename: str) -> list[dict]:
        """
        Load document from raw bytes (used when files arrive via HTTP upload).
        Writes to a temp file, loads, then cleans up.
        """
        import tempfile
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return self.load_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    # ── Private loaders ──────────────────────────────────────────────────────

    def _load_txt(self, path: str, source: str) -> list[dict]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return [{"content": content, "source": source, "metadata": {"type": "text"}}]

    def _load_pdf(self, path: str, source: str) -> list[dict]:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Install pypdf: pip install pypdf")

        reader = PdfReader(path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "content": text,
                    "source": source,
                    "metadata": {"type": "pdf", "page": i + 1}
                })
        logger.info(f"Extracted {len(pages)} pages from {source}")
        return pages

    def _load_docx(self, path: str, source: str) -> list[dict]:
        try:
            from docx import Document
        except ImportError:
            raise ImportError("Install python-docx: pip install python-docx")

        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)
        return [{"content": content, "source": source, "metadata": {"type": "docx"}}]
