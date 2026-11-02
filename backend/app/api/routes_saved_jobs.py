from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import SavedJob, User
from app.models.schemas import JobListing

router = APIRouter(prefix="/api/saved-jobs", tags=["saved-jobs"])

Status = Literal["saved", "applied", "interview", "offer", "rejected"]
MAX_SAVED = 200


class SavedJobIn(BaseModel):
    job: JobListing
    status: Status = "saved"


class SavedJobUpdate(BaseModel):
    status: Status | None = None
    notes: str | None = Field(default=None, max_length=2000)


def _out(r: SavedJob) -> dict:
    return {
        "id": r.id,
        "status": r.status,
        "notes": r.notes,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "job": {
            "id": r.job_id,
            "title": r.title,
            "company": r.company,
            "location": r.location,
            "description": r.description,
            "url": r.url,
            "source": r.source,
        },
    }


def _get_owned(db: Session, user: User, saved_id: int) -> SavedJob:
    row = (
        db.query(SavedJob)
        .filter(SavedJob.id == saved_id, SavedJob.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Saved job not found.")
    return row


@router.get("")
async def list_saved(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.updated_at.desc())
        .limit(MAX_SAVED)
        .all()
    )
    return [_out(r) for r in rows]


@router.post("")
async def save_job(
    body: SavedJobIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = body.job
    existing = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.job_id == job.id)
        .first()
    )
    if existing:  # idempotent: saving twice just returns the same row
        return _out(existing)

    count = db.query(SavedJob).filter(SavedJob.user_id == current_user.id).count()
    if count >= MAX_SAVED:
        raise HTTPException(
            status_code=400, detail=f"You can save up to {MAX_SAVED} jobs."
        )

    row = SavedJob(
        user_id=current_user.id,
        job_id=job.id[:200],
        title=job.title[:300],
        company=job.company[:300],
        location=job.location[:200],
        description=job.description[:4000],
        url=job.url[:1000],
        source=job.source[:30],
        status=body.status,
        notes="",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/{saved_id}")
async def update_saved(
    saved_id: int,
    body: SavedJobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned(db, current_user, saved_id)
    if body.status is not None:
        row.status = body.status
    if body.notes is not None:
        row.notes = body.notes
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{saved_id}", status_code=204)
async def delete_saved(
    saved_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    row = _get_owned(db, current_user, saved_id)
    db.delete(row)
    db.commit()
    return Response(status_code=204)
