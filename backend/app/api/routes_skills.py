import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.agents.skill_gap_agent import run_skill_gap_agent
from app.models.schemas import SkillGapRequest, SkillGapResponse
from app.rate_limit import limiter

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/gap", response_model=SkillGapResponse)
@limiter.limit("15/minute")
async def skill_gap(request: Request, req: SkillGapRequest):
    try:
        return await asyncio.to_thread(run_skill_gap_agent, req.profile, req.job)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Skill gap analysis failed: {exc}"
        ) from exc
