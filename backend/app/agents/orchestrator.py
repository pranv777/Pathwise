"""Orchestrator Agent.

`run_chat_orchestrator()` serves the free-form chat endpoint. The orchestrator
LLM reasons about which single agent/tool best answers the user's message (job
search via MCP, GitHub analysis via MCP, skill gap, learning roadmap, interview
prep, or a plain RAG-grounded answer) and dispatches to it. This is what makes
routing genuinely agentic rather than a fixed if/else over keywords.
"""

from __future__ import annotations

import asyncio
import json
import logging

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.admin.tracking import track_agent
from app.agents.interview_agent import run_interview_generate
from app.agents.learning_agent import run_learning_agent
from app.agents.memory import add_turn, get_messages
from app.agents.skill_gap_agent import run_skill_gap_agent
from app.mcp_tools.mcp_client import MCPToolError, call_github_analysis, call_job_search
from app.models.llm_outputs import RouteOut
from app.models.schemas import JobListing, StudentProfile
from app.rag.vector_store import search
from app.utils.llm import get_llm, response_text
from app.utils.structured import invoke_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chat orchestrator — intent routing over agents/tools
# ---------------------------------------------------------------------------
VALID_ROUTES = {
    "job_search",
    "github_analysis",
    "skill_gap",
    "learning",
    "interview",
    "rag_answer",
}

ROUTER_SYSTEM_PROMPT = """You are the Orchestrator Agent for a college placement assistant.
Given the conversation so far and the user's latest message, decide the single best route.
Respond with ONLY valid JSON (no markdown fences):


{
  "route": "job_search" | "github_analysis" | "skill_gap" | "learning" | "interview" | "rag_answer",
  "reasoning": "one sentence on why this route",
  "job_query": "extracted search query if route is job_search, else empty string",
  "github_username": "extracted username if route is github_analysis, else empty string",
  "role": "target job role if route is skill_gap or interview, else empty string",
  "skills": ["skills to learn if route is learning, else empty list"]
}

Routing guide:
- job_search: user wants to find jobs/internships/openings (needs the MCP job-search tool).
- github_analysis: user wants a GitHub profile/repos analyzed (needs the MCP GitHub tool).
- skill_gap: user asks what skills they're missing for a role.
- learning: user asks how to learn/prepare for specific skills.
- interview: user asks for interview questions or practice for a role.
- rag_answer: general career-guidance question answerable from the knowledge base.
"""


async def _rag_answer(
    message: str, user_id: int | None, history: list[BaseMessage]
) -> str:
    shared = await asyncio.to_thread(search, message, 4)  # shared KB only
    mine = (
        await asyncio.to_thread(search, message, 2, "resume", user_id)
        if user_id is not None
        else []
    )
    context = "\n---\n".join(d.page_content for d, _ in shared)
    resume_ctx = "\n---\n".join(d.page_content for d, _ in mine)

    messages = [
        SystemMessage(
            content="You are a helpful college placement assistant. Answer using the "
            "provided context where relevant. Format your response in markdown — use "
            "**bold** for key terms, bullet points or numbered lists for multi-part "
            "answers, and short paragraphs. Be concise and practical."
        ),
        *history,
        HumanMessage(
            content=f"CONTEXT:\n{context}\n\n"
            f"CANDIDATE RESUME EXCERPTS:\n{resume_ctx or 'none'}\n\n"
            f"QUESTION: {message}"
        ),
    ]
    return response_text(await get_llm(temperature=0.4).ainvoke(messages))


async def _role_as_job(role: str) -> JobListing:
    """Build a synthetic JobListing from RAG job-description templates."""
    docs = await asyncio.to_thread(search, f"{role} requirements", 2, "job_description")
    description = "\n".join(d.page_content for d, _ in docs) or f"{role} role"
    return JobListing(
        id="chat-role", title=role, company="(from chat)", description=description
    )


async def _route_and_run(
    message: str,
    profile: StudentProfile | None,
    user_id: int,
    history: list[BaseMessage],
) -> str:
    router_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        *history,
        HumanMessage(content=message),
    ]
    routed = await asyncio.to_thread(invoke_json, RouteOut, router_messages, 0.1)
    route = routed.route if routed.route in VALID_ROUTES else "rag_answer"
    logger.info("Orchestrator routed to %s", route)

    if route == "job_search":
        try:
            result = await call_job_search(routed.job_query or message, limit=5)
        except MCPToolError as exc:
            return f"I couldn't reach the job search tool right now: {exc}"
        jobs = result.get("jobs", [])
        if not jobs:
            return "I couldn't find matching openings right now."
        listing = "\n".join(
            f"- {j['title']} at {j['company']} ({j.get('location', '')})" for j in jobs
        )
        return f"Here are openings matching your query:\n\n{listing}"

    if route == "github_analysis":
        username = routed.github_username.strip()
        if not username:
            return "Which GitHub username should I analyze?"
        try:
            result = await call_github_analysis(username)  # called exactly once
        except MCPToolError as exc:
            return f"I couldn't reach the GitHub analysis tool right now: {exc}"
        if "error" in result:
            return f"Couldn't analyze that GitHub profile: {result['error']}"
        return result.get("summary", json.dumps(result))

    if route == "skill_gap":
        if not profile:
            return "Upload your resume first so I can compare your skills to the role."
        role = routed.role or message
        job = await _role_as_job(role)
        gap = await asyncio.to_thread(run_skill_gap_agent, profile, job)
        ranked = "\n".join(f"{i}. {s}" for i, s in enumerate(gap.priority_order, 1))
        return f"For **{role}**, here are your gaps in priority order:\n\n{ranked}\n\n{gap.explanation}"

    if route == "learning":
        skills = [s for s in routed.skills if isinstance(s, str) and s]
        if skills:
            roadmap = await asyncio.to_thread(run_learning_agent, skills)
            lines = [
                f"**{i}. {item.skill}** (~{item.estimated_weeks}w)\n"
                + "\n".join(f"   - {r}" for r in item.resources)
                for i, item in enumerate(roadmap.roadmap, 1)
            ]
            return (
                "\n\n".join(lines)
                + f"\n\n_Total: ~{roadmap.total_estimated_weeks} weeks_"
            )

    if route == "interview":
        role = routed.role or message
        interview = await asyncio.to_thread(run_interview_generate, role, profile, 5)
        blocks = [
            f"**{i}. {q.question}** _({q.category})_\n\n{q.answer}"
            for i, q in enumerate(interview.questions, 1)
        ]
        return "\n\n---\n\n".join(blocks)

    # rag_answer, plus learning-without-skills fallback
    return await _rag_answer(message, user_id, history)


@track_agent("orchestrator")
async def run_chat_orchestrator(
    message: str,
    profile: StudentProfile | None,
    user_id: int,
    session_id: str = "default",
) -> str:
    history = get_messages(user_id, session_id)
    reply = await _route_and_run(message, profile, user_id, history)
    add_turn(user_id, session_id, message, reply)
    return reply
