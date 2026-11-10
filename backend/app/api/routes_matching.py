import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.agents.job_matching_agent import run_job_matching_agent
from app.models.schemas import JobMatchRequest, JobMatchResponse
from app.rate_limit import limiter

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/score", response_model=JobMatchResponse)
@limiter.limit("15/minute")
async def score_match(request: Request, req: JobMatchRequest):
    try:
        return await asyncio.to_thread(run_job_matching_agent, req.profile, req.job)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Job matching failed: {exc}"
        ) from exc
