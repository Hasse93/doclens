"""Recruiter-side matching: score and rank résumés against a job description.

This reuses the shared core (the same embeddings used for retrieval) to produce
a semantic similarity signal, and the LLM to produce an explainable judgement
with matched/missing skills. The two combine into a single headline score.
"""

import math

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.json_parse import parse_json_object
from app.core.llm import get_llm
from app.core.rag.prompts import build_match_prompt, MATCH_SYSTEM
from app.models.document import Document
from app.models.match_result import MatchResult
from app.schemas.recruitment import LlmMatch, MatchResultOut
from app.services.document_text import get_document_text

_TEXT_CHAR_LIMIT = 12000

# The LLM judgement is the headline signal; semantic similarity is a supporting
# sanity check, so it carries the smaller weight.
_LLM_WEIGHT = 0.7
_SEMANTIC_WEIGHT = 0.3


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _owned_ready(db: Session, owner_id: int, document_id: int, role: str) -> Document | None:
    doc = db.get(Document, document_id)
    if doc is None or doc.owner_id != owner_id or doc.role != role or doc.status != "ready":
        return None
    return doc


def run_match(
    db: Session, owner_id: int, job_id: int, resume_ids: list[int] | None
) -> tuple[Document, list[MatchResultOut]]:
    job = _owned_ready(db, owner_id, job_id, "job")
    if job is None:
        raise ValueError("Job description not found or not ready.")

    resumes = _select_resumes(db, owner_id, resume_ids)
    if not resumes:
        raise ValueError("No ready résumés to score.")

    llm = get_llm()
    job_text = get_document_text(db, job.id, _TEXT_CHAR_LIMIT)
    job_vector = llm.embed([job_text])[0]

    # Replace any previous results for this job so the stored set stays current.
    db.execute(delete(MatchResult).where(MatchResult.job_id == job.id))

    results: list[MatchResultOut] = []
    for resume in resumes:
        resume_text = get_document_text(db, resume.id, _TEXT_CHAR_LIMIT)

        resume_vector = llm.embed([resume_text])[0]
        semantic = round(_cosine_similarity(job_vector, resume_vector) * 100)

        raw = llm.generate(build_match_prompt(job_text, resume_text), system=MATCH_SYSTEM)
        judgement = LlmMatch.model_validate(parse_json_object(raw))

        score = round(_LLM_WEIGHT * judgement.overall_score + _SEMANTIC_WEIGHT * semantic)

        db.add(
            MatchResult(
                owner_id=owner_id,
                job_id=job.id,
                resume_id=resume.id,
                score=score,
                semantic_score=semantic,
                matched_skills=judgement.matched_skills,
                missing_skills=judgement.missing_skills,
                recommendation=judgement.summary,
            )
        )
        results.append(
            MatchResultOut(
                resume_id=resume.id,
                resume_title=resume.title,
                score=score,
                semantic_score=semantic,
                matched_skills=judgement.matched_skills,
                missing_skills=judgement.missing_skills,
                recommendation=judgement.summary,
            )
        )

    db.commit()
    results.sort(key=lambda r: r.score, reverse=True)
    return job, results


def _select_resumes(
    db: Session, owner_id: int, resume_ids: list[int] | None
) -> list[Document]:
    stmt = select(Document).where(
        Document.owner_id == owner_id,
        Document.role == "resume",
        Document.status == "ready",
    )
    if resume_ids:
        stmt = stmt.where(Document.id.in_(resume_ids))
    return list(db.execute(stmt).scalars().all())
