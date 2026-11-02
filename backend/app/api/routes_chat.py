import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_chat_orchestrator, run_full_workflow
from app.auth.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User, UserHistory
from app.models.schemas import (
    AgentStep,
    ChatRequest,
    ChatResponse,
    InterviewQuestion,
    JobListing,
    JobMatchResponse,
    LearningRoadmapResponse,
    SkillGapResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from app.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["orchestrator"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        reply, steps = await run_chat_orchestrator(
            req.message, req.profile, current_user.id, req.session_id
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Assistant failed: {exc}") from exc
    return ChatResponse(reply=reply, steps=steps)


@router.post("/workflow/run", response_model=WorkflowResponse)
@limiter.limit("5/minute")
async def run_workflow(
    request: Request,
    req: WorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        final_state = await run_full_workflow(
            req.profile, req.job_query, req.location or ""
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Workflow execution failed: {exc}"
        ) from exc

    db.add(
        UserHistory(
            user_id=current_user.id,
            kind="workflow_run",
            payload=json.dumps(
                {
                    "job": final_state.get("job"),
                    "match": final_state.get("match"),
                    "skill_gap": final_state.get("skill_gap"),
                    "roadmap": final_state.get("roadmap"),
                    "interview_questions": final_state.get("interview_questions"),
                },
                default=str,
            ),
        )
    )
    db.commit()

    job = JobListing(**final_state["job"]) if final_state.get("job") else None
    match = (
        JobMatchResponse(**final_state["match"]) if final_state.get("match") else None
    )
    skill_gap = (
        SkillGapResponse(**final_state["skill_gap"])
        if final_state.get("skill_gap")
        else None
    )
    roadmap = (
        LearningRoadmapResponse(**final_state["roadmap"])
        if final_state.get("roadmap")
        else None
    )
    interview_questions = [
        InterviewQuestion(**q) for q in final_state.get("interview_questions", [])
    ]
    steps = [AgentStep(**s) for s in final_state.get("steps", [])]

    return WorkflowResponse(
        steps=steps,
        job=job,
        match=match,
        skill_gap=skill_gap,
        roadmap=roadmap,
        interview_questions=interview_questions,
    )
