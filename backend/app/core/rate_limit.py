"""Per-IP rate limiting.

A single shared limiter, keyed by client IP, applied via decorators to the
expensive endpoints (uploads, LLM calls, auth) so a flood of requests can't
exhaust the Gemini quota or spam account creation. Cheap reads are left
unlimited so normal use — including dashboard status polling — is unaffected.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
