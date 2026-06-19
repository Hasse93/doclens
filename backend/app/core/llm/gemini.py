"""Google Gemini implementation of the LLM provider contract."""

import time
from collections.abc import Iterator
from typing import Callable, TypeVar

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

from app.config import settings
from app.core.llm.base import LLMProvider

T = TypeVar("T")

# Send embeddings in batches so a long document is a few requests, not one per
# chunk — far gentler on rate limits.
_EMBED_BATCH = 100


def _with_retry(call: Callable[[], T], *, retries: int = 4, base_delay: float = 2.0) -> T:
    """Retry transient rate-limit / availability errors with exponential backoff."""
    for attempt in range(retries):
        try:
            return call()
        except (ResourceExhausted, ServiceUnavailable):
            if attempt == retries - 1:
                raise
            time.sleep(base_delay * (2**attempt))
    raise RuntimeError("unreachable")  # pragma: no cover


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your environment to enable the AI features."
            )
        genai.configure(api_key=settings.gemini_api_key)
        self._chat_model = settings.chat_model
        self._embedding_model = settings.embedding_model
        self._embedding_dimension = settings.embedding_dimension

    def generate(self, prompt: str, system: str | None = None) -> str:
        model = genai.GenerativeModel(self._chat_model, system_instruction=system)
        response = _with_retry(lambda: model.generate_content(prompt))
        return (response.text or "").strip()

    def generate_stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        model = genai.GenerativeModel(self._chat_model, system_instruction=system)
        # The initial request is retried; once the stream starts we forward
        # chunks as they arrive.
        stream = _with_retry(lambda: model.generate_content(prompt, stream=True))
        for chunk in stream:
            text = getattr(chunk, "text", "")
            if text:
                yield text

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH):
            batch = texts[start : start + _EMBED_BATCH]
            result = _with_retry(
                lambda b=batch: genai.embed_content(
                    model=self._embedding_model,
                    content=b,
                    task_type="retrieval_document",
                    output_dimensionality=self._embedding_dimension,
                )
            )
            vectors.extend(result["embedding"])
        return vectors

    def embed_query(self, query: str) -> list[float]:
        result = _with_retry(
            lambda: genai.embed_content(
                model=self._embedding_model,
                content=query,
                task_type="retrieval_query",
                output_dimensionality=self._embedding_dimension,
            )
        )
        return result["embedding"]
