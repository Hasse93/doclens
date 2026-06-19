"""Vector similarity search over a document's chunks."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.llm import get_llm
from app.models.chunk import DocumentChunk
from app.models.document import Document


@dataclass
class RetrievedChunk:
    chunk_index: int
    page_number: int
    content: str
    distance: float


@dataclass
class MultiRetrievedChunk:
    document_id: int
    document_title: str
    page_number: int
    content: str
    distance: float


def retrieve(db: Session, document_id: int, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """Return the most relevant chunks for a query within one document.

    Uses pgvector cosine distance; lower distance means a closer match.
    """
    top_k = top_k or settings.retrieval_top_k
    query_embedding = get_llm().embed_query(query)

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, distance.label("distance"))
        .where(DocumentChunk.document_id == document_id)
        .order_by(distance)
        .limit(top_k)
    )

    results = db.execute(stmt).all()
    return [
        RetrievedChunk(
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            content=chunk.content,
            distance=float(dist),
        )
        for chunk, dist in results
    ]


def retrieve_multi(
    db: Session, document_ids: list[int], query: str, top_k: int | None = None
) -> list[MultiRetrievedChunk]:
    """Retrieve the most relevant chunks across several documents at once.

    Each result carries its source document so answers can cite which document
    and page the information came from.
    """
    if not document_ids:
        return []

    top_k = top_k or settings.retrieval_top_k
    query_embedding = get_llm().embed_query(query)

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, Document.title, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.document_id.in_(document_ids))
        .order_by(distance)
        .limit(top_k)
    )

    results = db.execute(stmt).all()
    return [
        MultiRetrievedChunk(
            document_id=chunk.document_id,
            document_title=title,
            page_number=chunk.page_number,
            content=chunk.content,
            distance=float(dist),
        )
        for chunk, title, dist in results
    ]
