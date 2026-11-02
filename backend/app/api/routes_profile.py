from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User, UserHistory
from app.models.schemas import StudentProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])

KIND_PROFILE = "profile"


def save_user_profile(db: Session, user_id: int, profile: StudentProfile) -> None:
    """Create or replace this user's saved profile."""
    payload = profile.model_dump_json()  # raw_text is excluded by the schema
    row = (
        db.query(UserHistory)
        .filter(UserHistory.user_id == user_id, UserHistory.kind == KIND_PROFILE)
        .first()
    )
    if row:
        row.payload = payload
        row.created_at = datetime.now(UTC)
    else:
        db.add(UserHistory(user_id=user_id, kind=KIND_PROFILE, payload=payload))
    db.commit()


@router.get("")
async def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = (
        db.query(UserHistory)
        .filter(
            UserHistory.user_id == current_user.id, UserHistory.kind == KIND_PROFILE
        )
        .first()
    )
    return {"profile": json.loads(row.payload) if row else None}


@router.put("")
async def put_profile(
    profile: StudentProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Keep user-edited lists bounded and tidy.
    profile.skills = [s.strip()[:60] for s in profile.skills if s.strip()][:100]
    profile.projects = [p.strip()[:300] for p in profile.projects if p.strip()][:30]
    save_user_profile(db, current_user.id, profile)
    return {"status": "saved"}
