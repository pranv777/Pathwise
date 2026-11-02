from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import (
    routes_account,
    routes_auth,
    routes_campus,
    routes_chat,
    routes_github,
    routes_history,
    routes_interview,
    routes_jobs,
    routes_learning,
    routes_matching,
    routes_profile,
    routes_resume,
    routes_saved_jobs,
    routes_skills,
)
from app.auth.dependencies import get_current_user
from app.config import settings
from app.rag.ingest import seed_if_empty
from app.rate_limit import limiter

logger = logging.getLogger("startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY is not set: agent endpoints will fail.")
    elif settings.seed_on_startup:
        try:
            logger.info("KB seed: %s", await asyncio.to_thread(seed_if_empty))
        except Exception:
            logger.exception("Knowledge base seeding failed")
    yield


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

app.include_router(routes_auth.router)  # public — no auth required to log in

protected = [Depends(get_current_user)]
app.include_router(routes_resume.router, dependencies=protected)
app.include_router(routes_jobs.router, dependencies=protected)
app.include_router(routes_matching.router, dependencies=protected)
app.include_router(routes_skills.router, dependencies=protected)
app.include_router(routes_learning.router, dependencies=protected)
app.include_router(routes_interview.router, dependencies=protected)
app.include_router(routes_chat.router, dependencies=protected)
app.include_router(routes_github.router, dependencies=protected)
app.include_router(routes_history.router, dependencies=protected)
app.include_router(routes_profile.router, dependencies=protected)
app.include_router(routes_account.router, dependencies=protected)
app.include_router(routes_saved_jobs.router, dependencies=protected)
app.include_router(routes_campus.router, dependencies=protected)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)


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
