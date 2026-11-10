import asyncio

from fastapi import APIRouter, HTTPException, Request

from app.agents.learning_agent import run_learning_agent
from app.models.schemas import LearningRequest, LearningRoadmapResponse
from app.rate_limit import limiter

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.post("/roadmap", response_model=LearningRoadmapResponse)
@limiter.limit("10/minute")
async def learning_roadmap(request: Request, req: LearningRequest):
    try:
        return await asyncio.to_thread(
            run_learning_agent, req.missing_skills, req.context
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Learning roadmap generation failed: {exc}"
        ) from exc
