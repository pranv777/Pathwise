from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.pdf_parser import extract_text_from_pdf
from app.agents.resume_agent import run_resume_agent
from app.models.schemas import ResumeAnalysisResponse
from app.rag.vector_store import add_document

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/upload", response_model=ResumeAnalysisResponse)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    file_bytes = await file.read()
    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read this PDF: {exc}")

    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF.")

    try:
        profile = run_resume_agent(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Resume parsing failed: {exc}")    

    # Index the resume itself into the knowledge base so future RAG queries
    # (e.g. "what does my resume say about X") can retrieve it.
    add_document(text=text, source=file.filename, doc_type="resume")

    summary = (
        f"Extracted {len(profile.skills)} skills, {len(profile.projects)} projects, "
        f"{len(profile.experience)} experience entries."
    )
    return ResumeAnalysisResponse(profile=profile, summary=summary)
