"""LLM provider selection.

A single cached instance is shared across requests so that SDK clients and
their connection pools are reused.
"""

from functools import lru_cache

from app.config import settings
from app.core.llm.base import LLMProvider
from app.core.llm.gemini import GeminiProvider

_PROVIDERS = {
    "gemini": GeminiProvider,
}


@lru_cache
def get_llm() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider not in _PROVIDERS:
        raise RuntimeError(
            f"Unknown LLM provider '{provider}'. Available: {', '.join(_PROVIDERS)}."
        )
    return _PROVIDERS[provider]()


__all__ = ["LLMProvider", "get_llm"]
