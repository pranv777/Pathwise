from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.agents.interview_agent import run_interview_evaluate, run_interview_generate
from app.models.schemas import (
    InterviewEvaluateRequest,
    InterviewEvaluateResponse,
    InterviewGenerateRequest,
    InterviewGenerateResponse,
)

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/generate", response_model=InterviewGenerateResponse)
async def generate_questions(req: InterviewGenerateRequest):
    try:
        return await asyncio.to_thread(
            run_interview_generate, req.role, req.profile, req.num_questions
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Interview question generation failed: {exc}"
        ) from exc


@router.post("/evaluate", response_model=InterviewEvaluateResponse)
async def evaluate_answer(req: InterviewEvaluateRequest):
    try:
        return await asyncio.to_thread(
            run_interview_evaluate, req.question, req.answer, req.role
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Interview evaluation failed: {exc}"
        ) from exc
