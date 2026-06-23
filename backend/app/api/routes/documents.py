"""Document routes: upload, list, retrieve, extract, and delete."""

import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.core.rate_limit import limiter
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut, ResearchExtraction
from app.schemas.recruitment import RecruitmentExtraction
from app.services import document_service, extraction_service, report_service

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_BYTES = settings.max_upload_mb * 1024 * 1024
_VALID_MODES = {"research", "recruitment"}
# Allowed roles per mode; research documents are always neutral "document".
_VALID_ROLES = {"document", "job", "resume"}


def _get_owned_document(db: Session, document_id: int, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/hour")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    mode: str = Form("research"),
    role: str = Form("document"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are supported"
        )
    if mode not in _VALID_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown mode")
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty")
    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit",
        )

    document = document_service.create_document(
        db,
        owner_id=user.id,
        title=(title or file.filename or "Untitled").strip(),
        filename=file.filename or "document.pdf",
        mode=mode,
        role=role,
    )

    # Heavy work (extraction, embeddings, summary) runs after the response so the
    # upload returns immediately; the client polls status until it is "ready".
    background_tasks.add_task(document_service.process_document, document.id, file_bytes)
    return DocumentOut.model_validate(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[DocumentOut]:
    stmt = (
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    )
    documents = db.execute(stmt).scalars().all()
    return [DocumentOut.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentOut:
    return DocumentOut.model_validate(_get_owned_document(db, document_id, user))


@router.get("/{document_id}/extraction", response_model=ResearchExtraction | RecruitmentExtraction)
def get_extraction(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ResearchExtraction | RecruitmentExtraction:
    document = _get_owned_document(db, document_id, user)
    if document.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still processing; try again once it is ready",
        )
    # Same pipeline, different schema — the mode selects which fields to pull.
    if document.mode == "recruitment":
        return extraction_service.extract_recruitment_fields(db, document_id)
    return extraction_service.extract_research_fields(db, document_id)


@router.get("/{document_id}/report")
def export_report(
    document_id: int,
    format: str = Query("md", pattern="^(md|pdf)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    document = _get_owned_document(db, document_id, user)
    if document.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still processing; try again once it is ready",
        )
    # A filesystem-safe filename derived from the title.
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", document.title).strip("-") or "report"

    if format == "pdf":
        pdf_bytes = report_service.build_pdf_report(db, document)
        return Response(
            pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
        )

    markdown = report_service.build_markdown_report(db, document)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    document = _get_owned_document(db, document_id, user)
    db.delete(document)
    db.commit()
