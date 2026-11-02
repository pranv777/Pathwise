from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.agents.job_matching_agent import run_job_matching_agent
from app.models.schemas import JobMatchRequest, JobMatchResponse

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/score", response_model=JobMatchResponse)
async def score_match(req: JobMatchRequest):
    try:
        return await asyncio.to_thread(run_job_matching_agent, req.profile, req.job)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Job matching failed: {exc}"
        ) from exc
