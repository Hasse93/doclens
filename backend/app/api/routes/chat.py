"""Chat routes: per-document Q&A (sync + streaming), history, and multi-document."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    MultiChatRequest,
    MultiChatResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/documents", tags=["chat"])


def _ready_research_ids(db: Session, owner_id: int, requested: list[int] | None) -> list[int]:
    """Resolve which documents to search, scoped to the owner's ready research docs."""
    stmt = select(Document.id).where(
        Document.owner_id == owner_id,
        Document.mode == "research",
        Document.status == "ready",
    )
    if requested:
        stmt = stmt.where(Document.id.in_(requested))
    return list(db.execute(stmt).scalars().all())


def _ready_owned_document(db: Session, document_id: int, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still processing; try again once it is ready",
        )
    return document


@router.post("/{document_id}/chat", response_model=ChatResponse)
def chat(
    document_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    _ready_owned_document(db, document_id, user)
    return chat_service.answer_question(db, document_id, user.id, payload.question)


@router.post("/{document_id}/chat/stream")
def chat_stream(
    document_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    _ready_owned_document(db, document_id, user)
    generator = chat_service.stream_answer(db, document_id, user.id, payload.question)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{document_id}/messages", response_model=list[ChatMessageOut])
def get_messages(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChatMessageOut]:
    _ready_owned_document(db, document_id, user)
    return [ChatMessageOut.model_validate(m) for m in chat_service.history(db, document_id)]


@router.delete("/{document_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
def clear_messages(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    _ready_owned_document(db, document_id, user)
    chat_service.clear_history(db, document_id)


@router.post("/ask", response_model=MultiChatResponse)
def ask_across_documents(
    payload: MultiChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MultiChatResponse:
    document_ids = _ready_research_ids(db, user.id, payload.document_ids)
    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ready documents to search.",
        )
    return chat_service.answer_across_documents(db, document_ids, payload.question)
