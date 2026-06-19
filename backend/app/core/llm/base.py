"""Provider-agnostic interface for language and embedding models.

Every concrete provider implements this contract, so the rest of the
application never imports a vendor SDK directly. Swapping providers is a
configuration change, not a code change.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """Contract for chat generation and text embeddings."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Return a single completion for the given prompt."""

    def generate_stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        """Yield the completion incrementally.

        Providers that support token streaming should override this; the default
        yields the full result once so callers work with any provider.
        """
        yield self.generate(prompt, system)

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in the same order."""

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query.

        Providers that distinguish document and query embeddings should
        override this; the default reuses the document embedding path.
        """
        return self.embed([query])[0]
