from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models.schemas import SkillGapRequest, SkillGapResponse
from app.agents.skill_gap_agent import run_skill_gap_agent

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/gap", response_model=SkillGapResponse)
async def skill_gap(req: SkillGapRequest):
    try:
        return run_skill_gap_agent(req.profile, req.job)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Skill gap analysis failed: {exc}")
