"""Document ingestion and processing.

The processing pipeline runs as a background task after upload:
extract -> chunk -> embed -> persist -> summarise. Failures are recorded on the
document so the UI can surface a clear status instead of hanging.
"""

import logging

from sqlalchemy.orm import Session

from app.core.llm import get_llm
from app.core.rag.chunker import chunk_pages
from app.core.rag.extractor import extract_pages
from app.core.rag.prompts import build_summary_prompt, SUMMARY_SYSTEM
from app.database import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document

logger = logging.getLogger(__name__)

# Cap the text sent to the summariser so a very long paper stays within a single
# request; the opening pages reliably contain the abstract and introduction.
_SUMMARY_CHAR_LIMIT = 12000


def create_document(
    db: Session, owner_id: int, title: str, filename: str, mode: str, role: str
) -> Document:
    document = Document(
        owner_id=owner_id,
        title=title,
        filename=filename,
        mode=mode,
        role=role,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def process_document(document_id: int, file_bytes: bytes) -> None:
    """Run the full ingestion pipeline for one document.

    Opens its own session because it is invoked from a background task that
    outlives the originating request.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return

        document.status = "processing"
        db.commit()

        pages = extract_pages(file_bytes)
        if not pages:
            raise ValueError("No extractable text was found in this PDF.")

        chunks = chunk_pages(pages)
        embeddings = get_llm().embed([c.content for c in chunks])

        db.add_all(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        )

        document.page_count = pages[-1].page_number
        document.summary = _summarise(pages)
        document.status = "ready"
        db.commit()
    except Exception as exc:  # noqa: BLE001 - record any failure for the UI
        logger.exception("Failed to process document %s", document_id)
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = "failed"
            document.error = str(exc)
            db.commit()
    finally:
        db.close()


def _summarise(pages) -> str:
    joined = "\n\n".join(p.text for p in pages)[:_SUMMARY_CHAR_LIMIT]
    return get_llm().generate(build_summary_prompt(joined), system=SUMMARY_SYSTEM)
