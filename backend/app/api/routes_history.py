from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User, UserHistory
from app.models.schemas import HistorySnapshot

router = APIRouter(prefix="/api/history", tags=["history"])

KIND_ANALYSIS = "analysis"


@router.get("")
async def get_history(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.query(UserHistory)
        .filter(
            UserHistory.user_id == current_user.id,
            UserHistory.kind == KIND_ANALYSIS,
        )
        .order_by(UserHistory.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "created_at": r.created_at,
            "payload": json.loads(r.payload),
        }
        for r in rows
    ]


def _same_job(a: dict, b: dict) -> bool:
    return (a.get("id"), a.get("title"), a.get("company")) == (
        b.get("id"),
        b.get("title"),
        b.get("company"),
    )


@router.post("/snapshot")
async def save_snapshot(
    snap: HistorySnapshot,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update this user's analysis record for one job."""
    data = snap.model_dump()
    payload = json.dumps(data, default=str)

    recent = (
        db.query(UserHistory)
        .filter(
            UserHistory.user_id == current_user.id,
            UserHistory.kind == KIND_ANALYSIS,
        )
        .order_by(UserHistory.created_at.desc())
        .limit(50)
        .all()
    )
    existing = next(
        (
            r
            for r in recent
            if _same_job(json.loads(r.payload).get("job", {}), data["job"])
        ),
        None,
    )

    if existing:
        existing.payload = payload
        existing.created_at = datetime.now(UTC)  # bump to top of history
    else:
        db.add(
            UserHistory(user_id=current_user.id, kind=KIND_ANALYSIS, payload=payload)
        )
    db.commit()
    return {"status": "saved"}
