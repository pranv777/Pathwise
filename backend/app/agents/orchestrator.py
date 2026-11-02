"""Orchestrator Agent.

Two responsibilities:

1. `build_workflow_graph()` — a LangGraph StateGraph wiring the full
   pipeline: search jobs (MCP tool) -> job matching -> skill gap ->
   learning roadmap -> interview prep. Used by the "run full workflow"
   endpoint.

2. `run_chat_orchestrator()` — for the free-form chat endpoint. The
   orchestrator LLM reasons about which single agent/tool best answers
   the user's message (job search via MCP, GitHub analysis via MCP,
   skill gap, learning roadmap, interview prep, or a plain RAG-grounded
   answer) and dispatches to it. This is what makes routing genuinely
   agentic rather than a fixed if/else over keywords.
"""

from __future__ import annotations

import asyncio
import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.interview_agent import run_interview_generate
from app.agents.job_matching_agent import run_job_matching_agent
from app.agents.learning_agent import run_learning_agent
from app.agents.memory import add_turn, get_messages
from app.agents.skill_gap_agent import run_skill_gap_agent
from app.agents.state import WorkflowState, log_step
from app.mcp_tools.mcp_client import MCPToolError, call_github_analysis, call_job_search
from app.models.llm_outputs import RouteOut
from app.models.schemas import AgentStep, JobListing, StudentProfile
from app.rag.vector_store import search
from app.utils.llm import get_llm, response_text
from app.utils.structured import invoke_json

# ---------------------------------------------------------------------------
# 1. Full-pipeline LangGraph workflow
# ---------------------------------------------------------------------------


async def _node_search_jobs(state: WorkflowState) -> WorkflowState:
    try:
        result = await call_job_search(
            state["job_query"], state.get("location", ""), limit=1
        )
    except MCPToolError as exc:
        log_step(state, "Orchestrator", "MCP tool call: search_jobs failed", str(exc))
        return state

    jobs = result.get("jobs", [])
    if jobs:
        state["job"] = jobs[0]
        log_step(
            state,
            "Orchestrator",
            "MCP tool call: search_jobs",
            f"Found '{jobs[0]['title']}' at {jobs[0]['company']} via {result.get('tool_used')}",
        )
    else:
        log_step(state, "Orchestrator", "MCP tool call: search_jobs", "No jobs found")
    return state


def _node_match(state: WorkflowState) -> WorkflowState:
    if not state.get("job"):
        return state
    profile = StudentProfile(**state["profile"])
    job = JobListing(**state["job"])
    match = run_job_matching_agent(profile, job)
    state["match"] = match.model_dump()
    log_step(
        state,
        "Job Matching Agent",
        "Scored resume against job description",
        f"Match score: {match.match_score}/100",
    )
    return state


def _node_skill_gap(state: WorkflowState) -> WorkflowState:
    if not state.get("job"):
        return state
    profile = StudentProfile(**state["profile"])
    job = JobListing(**state["job"])
    gap = run_skill_gap_agent(profile, job)
    state["skill_gap"] = gap.model_dump()
    log_step(
        state,
        "Skill Gap Agent",
        "Identified missing skills",
        f"{len(gap.missing_skills)} gaps found: {', '.join(gap.missing_skills[:5])}",
    )
    return state


def _node_learning(state: WorkflowState) -> WorkflowState:
    missing = state.get("skill_gap", {}).get("priority_order", [])
    if not missing:
        return state
    roadmap = run_learning_agent(missing)
    state["roadmap"] = roadmap.model_dump()
    log_step(
        state,
        "Learning Recommendation Agent",
        "Built learning roadmap (RAG-grounded)",
        f"{len(roadmap.roadmap)} skills, ~{roadmap.total_estimated_weeks} weeks total",
    )
    return state


def _node_interview(state: WorkflowState) -> WorkflowState:
    if not state.get("job"):
        return state
    profile = StudentProfile(**state["profile"])
    job = JobListing(**state["job"])
    result = run_interview_generate(job.title, profile, num_questions=5)
    state["interview_questions"] = [q.model_dump() for q in result.questions]
    log_step(
        state,
        "Interview Agent",
        "Generated role-specific questions (RAG-grounded)",
        f"{len(result.questions)} questions for '{job.title}'",
    )
    return state


_workflow_graph = None


def build_workflow_graph():
    global _workflow_graph
    if _workflow_graph is not None:
        return _workflow_graph

    graph = StateGraph(WorkflowState)

    # Node IDs must not duplicate keys in WorkflowState.
    graph.add_node("search_jobs", _node_search_jobs)
    graph.add_node("run_matching", _node_match)
    graph.add_node("analyze_skill_gaps", _node_skill_gap)
    graph.add_node("build_learning_roadmap", _node_learning)
    graph.add_node("generate_interview_questions", _node_interview)

    graph.set_entry_point("search_jobs")
    graph.add_edge("search_jobs", "run_matching")
    graph.add_edge("run_matching", "analyze_skill_gaps")
    graph.add_edge("analyze_skill_gaps", "build_learning_roadmap")
    graph.add_edge("build_learning_roadmap", "generate_interview_questions")
    graph.add_edge("generate_interview_questions", END)

    _workflow_graph = graph.compile()
    return _workflow_graph


async def run_full_workflow(
    profile: StudentProfile, job_query: str, location: str = ""
) -> WorkflowState:
    app_graph = build_workflow_graph()
    initial_state: WorkflowState = {
        "profile": profile.model_dump(),
        "job_query": job_query,
        "location": location,
        "steps": [],
    }
    log_step(
        initial_state, "Orchestrator", "Starting full workflow", f"Query: {job_query!r}"
    )
    return await app_graph.ainvoke(initial_state)


# ---------------------------------------------------------------------------
# 2. Chat orchestrator — intent routing over agents/tools
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
) -> tuple[str, list[AgentStep]]:
    steps: list[AgentStep] = []
    router_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        *history,
        HumanMessage(content=message),
    ]
    routed = await asyncio.to_thread(invoke_json, RouteOut, router_messages, 0.1)
    route = routed.route if routed.route in VALID_ROUTES else "rag_answer"

    steps.append(
        AgentStep(
            agent="Orchestrator",
            action=f"Routed to: {route}",
            detail=routed.reasoning,
        )
    )

    if route == "job_search":
        try:
            result = await call_job_search(routed.job_query or message, limit=5)
        except MCPToolError as exc:
            steps.append(
                AgentStep(
                    agent="Job Search (MCP)", action="Tool call failed", detail=str(exc)
                )
            )
            return f"I couldn't reach the job search tool right now: {exc}", steps
        jobs = result.get("jobs", [])
        steps.append(
            AgentStep(
                agent="Job Search (MCP)",
                action="Called search_jobs tool",
                detail=f"tool_used={result.get('tool_used')}, {len(jobs)} results",
            )
        )
        if not jobs:
            return "I couldn't find matching openings right now.", steps
        listing = "\n".join(
            f"- {j['title']} at {j['company']} ({j.get('location', '')})" for j in jobs
        )
        return f"Here are openings matching your query:\n\n{listing}", steps

    if route == "github_analysis":
        username = routed.github_username.strip()
        if not username:
            return "Which GitHub username should I analyze?", steps
        try:
            result = await call_github_analysis(username)  # called exactly once
        except MCPToolError as exc:
            steps.append(
                AgentStep(
                    agent="GitHub Analysis (MCP)",
                    action="Tool call failed",
                    detail=str(exc),
                )
            )
            return f"I couldn't reach the GitHub analysis tool right now: {exc}", steps
        steps.append(
            AgentStep(
                agent="GitHub Analysis (MCP)",
                action="Called analyze_github_profile tool",
                detail=username,
            )
        )
        if "error" in result:
            return f"Couldn't analyze that GitHub profile: {result['error']}", steps
        return result.get("summary", json.dumps(result)), steps

    if route == "skill_gap":
        if not profile:
            return (
                "Upload your resume first so I can compare your skills to the role.",
                steps,
            )
        role = routed.role or message
        job = await _role_as_job(role)
        gap = await asyncio.to_thread(run_skill_gap_agent, profile, job)
        steps.append(
            AgentStep(
                agent="Skill Gap Agent",
                action="Identified missing skills",
                detail=f"{len(gap.missing_skills)} gaps for '{role}'",
            )
        )
        ranked = "\n".join(f"{i}. {s}" for i, s in enumerate(gap.priority_order, 1))
        return (
            f"For **{role}**, here are your gaps in priority order:\n\n{ranked}\n\n{gap.explanation}",
            steps,
        )

    if route == "learning":
        skills = [s for s in routed.skills if isinstance(s, str) and s]
        if skills:
            roadmap = await asyncio.to_thread(run_learning_agent, skills)
            steps.append(
                AgentStep(
                    agent="Learning Recommendation Agent",
                    action="Built learning roadmap (RAG-grounded)",
                    detail=f"{len(roadmap.roadmap)} skills, ~{roadmap.total_estimated_weeks} weeks",
                )
            )
            lines = [
                f"**{i}. {item.skill}** (~{item.estimated_weeks}w)\n"
                + "\n".join(f"   - {r}" for r in item.resources)
                for i, item in enumerate(roadmap.roadmap, 1)
            ]
            return "\n\n".join(
                lines
            ) + f"\n\n_Total: ~{roadmap.total_estimated_weeks} weeks_", steps

    if route == "interview":
        role = routed.role or message
        interview = await asyncio.to_thread(run_interview_generate, role, profile, 5)
        steps.append(
            AgentStep(
                agent="Interview Agent",
                action="Generated role-specific questions (RAG-grounded)",
                detail=f"{len(interview.questions)} questions for '{role}'",
            )
        )
        blocks = [
            f"**{i}. {q.question}** _({q.category})_\n\n{q.answer}"
            for i, q in enumerate(interview.questions, 1)
        ]
        return "\n\n---\n\n".join(blocks), steps

    # rag_answer, plus learning-without-skills fallback
    steps.append(
        AgentStep(agent="RAG", action="Retrieved knowledge-base context", detail=route)
    )
    return await _rag_answer(message, user_id, history), steps


async def run_chat_orchestrator(
    message: str,
    profile: StudentProfile | None,
    user_id: int,
    session_id: str = "default",
) -> tuple[str, list[AgentStep]]:
    history = get_messages(user_id, session_id)
    reply, steps = await _route_and_run(message, profile, user_id, history)
    add_turn(user_id, session_id, message, reply)
    return reply, steps
