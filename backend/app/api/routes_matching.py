from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models.schemas import JobMatchRequest, JobMatchResponse
from app.agents.job_matching_agent import run_job_matching_agent

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/score", response_model=JobMatchResponse)
async def score_match(req: JobMatchRequest):
    try:
        return run_job_matching_agent(req.profile, req.job)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Job matching failed: {exc}")
