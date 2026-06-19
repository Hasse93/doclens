"""Document and structured-extraction schemas."""

from datetime import datetime

from pydantic import BaseModel, field_validator


class DocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    mode: str
    role: str
    status: str
    error: str | None
    page_count: int
    summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


def coerce_to_text(value):
    """Normalise a free-text field: a model may return a list or null."""
    if value is None:
        return None
    if isinstance(value, list):
        joined = "; ".join(str(item) for item in value if item)
        return joined or None
    return str(value)


def coerce_to_list(value):
    """Normalise a list field: a model may return a single string or null."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


class ResearchExtraction(BaseModel):
    """Validated shape of the structured data pulled from a research paper.

    The validators tolerate the small formatting differences models produce
    (e.g. a list where a string is expected), so the response is always valid.
    """

    title: str | None = None
    authors: list[str] = []
    methodology: str | None = None
    dataset: str | None = None
    key_findings: list[str] = []
    limitations: str | None = None

    _text = field_validator("title", "methodology", "dataset", "limitations", mode="before")(
        coerce_to_text
    )
    _lists = field_validator("authors", "key_findings", mode="before")(coerce_to_list)
