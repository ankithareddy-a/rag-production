"""
config.py

Centralized settings loaded from the .env file using pydantic-settings.
All configuration lives here — no magic strings scattered in code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_password: str = "ragpassword"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dims: int = 384

    # Redis index
    vector_index_name: str = "rag_docs"
    vector_doc_prefix: str = "doc:"

    # Retrieval
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Cache
    cache_threshold: float = 0.90

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


# Singleton instance
settings = Settings()
