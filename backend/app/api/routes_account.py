from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.agents.memory import clear_user
from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import SavedJob, User, UserHistory
from app.rag.vector_store import USER_SCOPED_TYPES, delete_user_documents

router = APIRouter(prefix="/api/me", tags=["account"])


@router.delete("/data", status_code=204)
async def delete_my_data(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """Delete the caller's resume vectors, saved profile, history and chat memory.

    The account itself is kept.
    """
    # Vectors first: if this fails nothing else is deleted and the user can retry.
    for doc_type in sorted(USER_SCOPED_TYPES):
        await asyncio.to_thread(delete_user_documents, current_user.id, doc_type)

    db.query(SavedJob).filter(SavedJob.user_id == current_user.id).delete(
        synchronize_session=False
    )
    db.query(UserHistory).filter(UserHistory.user_id == current_user.id).delete(
        synchronize_session=False
    )
    db.commit()
    clear_user(current_user.id)
    return Response(status_code=204)
