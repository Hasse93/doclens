"""Recruitment route: rank résumés against a job description."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.database import get_db
from app.models.user import User
from app.schemas.recruitment import MatchRequest, MatchResponse
from app.services import recruitment_service

router = APIRouter(prefix="/recruitment", tags=["recruitment"])


@router.post("/match", response_model=MatchResponse)
@limiter.limit("20/minute")
def match(
    request: Request,
    payload: MatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MatchResponse:
    try:
        job, results = recruitment_service.run_match(
            db, owner_id=user.id, job_id=payload.job_id, resume_ids=payload.resume_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return MatchResponse(job_id=job.id, job_title=job.title, results=results)
