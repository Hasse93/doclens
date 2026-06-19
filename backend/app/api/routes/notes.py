"""Note routes: create, list, and delete notes on a document."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut

router = APIRouter(prefix="/documents", tags=["notes"])


def _ensure_owned_document(db: Session, document_id: int, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/{document_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    document_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NoteOut:
    _ensure_owned_document(db, document_id, user)
    note = Note(owner_id=user.id, document_id=document_id, content=payload.content.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)


@router.get("/{document_id}/notes", response_model=list[NoteOut])
def list_notes(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[NoteOut]:
    _ensure_owned_document(db, document_id, user)
    stmt = (
        select(Note)
        .where(Note.document_id == document_id)
        .order_by(Note.created_at.desc())
    )
    return [NoteOut.model_validate(n) for n in db.execute(stmt).scalars().all()]


@router.delete("/{document_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    document_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    note = db.get(Note, note_id)
    if note is None or note.owner_id != user.id or note.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    db.delete(note)
    db.commit()
