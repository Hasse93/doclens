"""Helper for reconstructing a document's full text from its stored chunks."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk


def get_document_text(db: Session, document_id: int, char_limit: int | None = None) -> str:
    stmt = (
        select(DocumentChunk.content)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    text = "\n".join(db.execute(stmt).scalars().all())
    return text[:char_limit] if char_limit else text
