import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.agents.resume_agent import run_resume_agent
from app.api.routes_profile import save_user_profile
from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.models.schemas import ResumeAnalysisResponse
from app.rag.vector_store import add_document, delete_user_documents
from app.rate_limit import limiter
from app.utils.text_extraction import extract_text

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


@router.post("/upload", response_model=ResumeAnalysisResponse)
@limiter.limit("10/minute")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)  # bounded read
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large (max {settings.max_upload_mb} MB)."
        )

    try:
        text = await asyncio.to_thread(extract_text, filename, file_bytes)
    except ValueError as exc:  # unsupported extension
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not read this file: {exc}"
        ) from exc

    if not text.strip():
        raise HTTPException(
            status_code=422, detail="Could not extract text from this file."
        )

    try:
        profile = await asyncio.to_thread(run_resume_agent, text)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Resume parsing failed: {exc}"
        ) from exc

    # Replace (not append to) this user's previous resume in the vector store.
    await asyncio.to_thread(delete_user_documents, current_user.id, "resume")
    await asyncio.to_thread(add_document, text, filename, "resume", current_user.id)
    save_user_profile(db, current_user.id, profile)

    summary = (
        f"Extracted {len(profile.skills)} skills, {len(profile.projects)} projects, "
        f"{len(profile.experience)} experience entries."
    )
    return ResumeAnalysisResponse(profile=profile, summary=summary)
