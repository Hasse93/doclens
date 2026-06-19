"""Schema-validated structured extraction from a document.

Extraction is mode-aware: the pipeline is identical, only the prompt and the
target schema change between research papers and résumés.
"""

from sqlalchemy.orm import Session

from app.core.json_parse import parse_json_object
from app.core.llm import get_llm
from app.core.rag.prompts import (
    build_extraction_prompt,
    build_recruitment_extraction_prompt,
    EXTRACTION_SYSTEM,
    RECRUITMENT_EXTRACTION_SYSTEM,
)
from app.schemas.document import ResearchExtraction
from app.schemas.recruitment import RecruitmentExtraction
from app.services.document_text import get_document_text

_EXTRACTION_CHAR_LIMIT = 12000


def extract_research_fields(db: Session, document_id: int) -> ResearchExtraction:
    text = get_document_text(db, document_id, _EXTRACTION_CHAR_LIMIT)
    raw = get_llm().generate(build_extraction_prompt(text), system=EXTRACTION_SYSTEM)
    # Validation guarantees the documented shape regardless of model output.
    return ResearchExtraction.model_validate(parse_json_object(raw))


def extract_recruitment_fields(db: Session, document_id: int) -> RecruitmentExtraction:
    text = get_document_text(db, document_id, _EXTRACTION_CHAR_LIMIT)
    raw = get_llm().generate(
        build_recruitment_extraction_prompt(text), system=RECRUITMENT_EXTRACTION_SYSTEM
    )
    return RecruitmentExtraction.model_validate(parse_json_object(raw))
