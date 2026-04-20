"""
llm.py

Async wrapper around the Ollama local LLM server.

Ollama exposes an OpenAI-compatible REST API at localhost:11434.
We use httpx (async HTTP client) to communicate with it.

Two modes:
  generate()  — waits for the full response (simpler, good for APIs)
  stream()    — yields tokens as they arrive (better UX for chat UIs)

Error handling:
  - Connection refused → Ollama isn't running
  - Timeout → model is slow (first inference loads model into RAM)
  - Model not found → need to `ollama pull <model>`
"""

from __future__ import annotations

import json
import logging
import httpx

logger = logging.getLogger(__name__)


class OllamaLLM:
    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: int = 180,
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt and wait for the complete response.
        
        First call may take 10-30s to load the model into RAM.
        Subsequent calls are much faster.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,   # Low temp = more deterministic, factual answers
                "top_p": 0.9,
                "num_predict": 1024,  # Max tokens to generate
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "").strip()
                logger.info(
                    f"LLM generated {data.get('eval_count', '?')} tokens "
                    f"in {data.get('eval_duration', 0) / 1e9:.1f}s"
                )
                return answer

        except httpx.ConnectError:
            raise RuntimeError(
                "Cannot connect to Ollama. Make sure it's running: "
                "docker compose up -d ollama"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found. "
                    f"Pull it with: docker exec -it rag-ollama ollama pull {self.model}"
                )
            raise

    async def stream(self, prompt: str):
        """
        Async generator that yields text tokens as they are produced.
        
        Usage:
            async for token in llm.stream(prompt):
                print(token, end="", flush=True)
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.1, "top_p": 0.9},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        """Returns True if Ollama is reachable and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                models = [m["name"] for m in resp.json().get("models", [])]
                available = any(self.model in m for m in models)
                if not available:
                    logger.warning(
                        f"Model '{self.model}' not found in Ollama. "
                        f"Available: {models}"
                    )
                return available
        except Exception:
            return False
