"""Recruitment-mode schemas: résumé extraction and JD ↔ résumé matching."""

import re

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import coerce_to_list, coerce_to_text


def coerce_to_number(value):
    """Pull a number out of values like 6, "6", or "6 years"; else None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(\.\d+)?", str(value))
    return float(match.group()) if match else None


class RecruitmentExtraction(BaseModel):
    """Validated shape of the structured data pulled from a résumé.

    Validators tolerate the formatting variance models produce so the response
    is always valid.
    """

    name: str | None = None
    email: str | None = None
    current_title: str | None = None
    skills: list[str] = []
    years_experience: float | None = None
    education: list[str] = []

    _text = field_validator("name", "email", "current_title", mode="before")(coerce_to_text)
    _lists = field_validator("skills", "education", mode="before")(coerce_to_list)
    _years = field_validator("years_experience", mode="before")(coerce_to_number)


class LlmMatch(BaseModel):
    """Internal shape of the model's matching judgement."""

    overall_score: int = 0
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    summary: str = ""

    @field_validator("overall_score")
    @classmethod
    def _clamp(cls, value: int) -> int:
        return max(0, min(100, value))


class MatchRequest(BaseModel):
    job_id: int
    # When omitted, every ready résumé the user owns is scored.
    resume_ids: list[int] | None = Field(default=None)


class MatchResultOut(BaseModel):
    resume_id: int
    resume_title: str
    score: int
    semantic_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    recommendation: str


class MatchResponse(BaseModel):
    job_id: int
    job_title: str
    results: list[MatchResultOut]
