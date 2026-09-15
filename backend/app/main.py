from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import (
    routes_resume,
    routes_jobs,
    routes_matching,
    routes_skills,
    routes_learning,
    routes_interview,
    routes_chat,
    routes_rag,
    routes_github,
)

app = FastAPI(
    title="Placement & Career Assistant API",
    description="Agentic AI backend: Resume, Job Matching, Skill Gap, "
    "Learning, Interview and Orchestrator agents, backed by RAG + MCP.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_resume.router)
app.include_router(routes_jobs.router)
app.include_router(routes_matching.router)
app.include_router(routes_skills.router)
app.include_router(routes_learning.router)
app.include_router(routes_interview.router)
app.include_router(routes_chat.router)
app.include_router(routes_rag.router)
app.include_router(routes_github.router)


@app.on_event("startup")
async def check_config():
    if not settings.google_api_key:
        import logging
        logging.getLogger("startup").warning(
            "GOOGLE_API_KEY is not set — all agent endpoints will fail until it's configured in .env"
        )

@app.get("/")
async def root():
    return {"status": "ok", "service": "placement-career-assistant-api"}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "gemini_configured": bool(settings.google_api_key),
        "tavily_configured": bool(settings.tavily_api_key),
        "github_token_configured": bool(settings.github_token),
    }
