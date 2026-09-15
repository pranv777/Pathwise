from __future__ import annotations
import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    WorkflowRequest,
    WorkflowResponse,
    AgentStep,
    JobListing,
    JobMatchResponse,
    SkillGapResponse,
    LearningRoadmapResponse,
    InterviewQuestion,
)
from app.agents.orchestrator import run_chat_orchestrator, run_full_workflow

router = APIRouter(prefix="/api", tags=["orchestrator"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        reply, steps = run_chat_orchestrator(req.message, req.profile)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Assistant failed: {exc}")
    return ChatResponse(reply=reply, steps=steps)


@router.post("/workflow/run", response_model=WorkflowResponse)
async def run_workflow(req: WorkflowRequest):
    try:
        final_state = await asyncio.to_thread(
            run_full_workflow,
            req.profile,
            req.job_query,
            req.location or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Workflow execution failed: {exc}")

    job = JobListing(**final_state["job"]) if final_state.get("job") else None
    match = JobMatchResponse(**final_state["match"]) if final_state.get("match") else None
    skill_gap = SkillGapResponse(**final_state["skill_gap"]) if final_state.get("skill_gap") else None
    roadmap = LearningRoadmapResponse(**final_state["roadmap"]) if final_state.get("roadmap") else None
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
