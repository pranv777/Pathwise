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
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agents.state import WorkflowState, log_step
from app.models.schemas import StudentProfile, JobListing, AgentStep
from app.agents.job_matching_agent import run_job_matching_agent
from app.agents.skill_gap_agent import run_skill_gap_agent
from app.agents.learning_agent import run_learning_agent
from app.agents.interview_agent import run_interview_generate
from app.mcp_tools.mcp_client import MCPToolError, call_job_search, call_github_analysis
from app.rag.vector_store import search
from app.utils.llm import get_llm, extract_json


# ---------------------------------------------------------------------------
# 1. Full-pipeline LangGraph workflow
# ---------------------------------------------------------------------------

def _node_search_jobs(state: WorkflowState) -> WorkflowState:
    from app.mcp_tools.mcp_client import MCPToolError
    try:
        result = asyncio.run(
            call_job_search(state["job_query"], state.get("location", ""), limit=1)
        )
    except MCPToolError as exc:
        log_step(state, "Orchestrator", "MCP tool call: search_jobs failed", str(exc))
        return state

    jobs = result.get("jobs", [])
    if jobs:
        state["job"] = jobs[0]
        log_step(
            state, "Orchestrator", "MCP tool call: search_jobs",
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
        state, "Job Matching Agent", "Scored resume against job description",
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
        state, "Skill Gap Agent", "Identified missing skills",
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
        state, "Learning Recommendation Agent", "Built learning roadmap (RAG-grounded)",
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
        state, "Interview Agent", "Generated role-specific questions (RAG-grounded)",
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


def run_full_workflow(profile: StudentProfile, job_query: str, location: str = "") -> WorkflowState:
    app_graph = build_workflow_graph()
    initial_state: WorkflowState = {
        "profile": profile.model_dump(),
        "job_query": job_query,
        "location": location,
        "steps": [],
    }
    log_step(initial_state, "Orchestrator", "Starting full workflow", f"Query: {job_query!r}")
    final_state = app_graph.invoke(initial_state)
    return final_state


# ---------------------------------------------------------------------------
# 2. Chat orchestrator — intent routing over agents/tools
# ---------------------------------------------------------------------------

ROUTER_SYSTEM_PROMPT = """You are the Orchestrator Agent for a college placement assistant.
Given the user's message, decide the single best route. Respond with ONLY valid JSON
(no markdown fences):

{
  "route": "job_search" | "github_analysis" | "skill_gap" | "learning" | "interview" | "rag_answer",
  "reasoning": "one sentence on why this route",
  "job_query": "extracted search query if route is job_search, else empty string",
  "github_username": "extracted username if route is github_analysis, else empty string"
}

Routing guide:
- job_search: user wants to find jobs/internships/openings -> requires the MCP job-search tool (live/external data).
- github_analysis: user wants their (or someone's) GitHub profile/repos analyzed -> requires the MCP GitHub tool.
- skill_gap: user asks what skills they're missing for a role, without a specific job already selected.
- learning: user asks how to learn/prepare for a specific skill or set of skills.
- interview: user asks for interview questions or wants to practice interviewing.
- rag_answer: general career-guidance question answerable from the knowledge base (resume tips, application strategy, etc.)
"""


def _rag_answer(message: str) -> str:
    docs = search(message, k=4)
    context = "\n---\n".join(d.page_content for d, _ in docs)
    llm = get_llm(temperature=0.4)
    messages = [
        SystemMessage(
            content="You are a helpful college placement assistant. Answer using the "
            "provided context where relevant. Be concise and practical."
        ),
        HumanMessage(content=f"CONTEXT:\n{context}\n\nQUESTION: {message}"),
    ]
    return llm.invoke(messages).content


def run_chat_orchestrator(message: str, profile: StudentProfile | None) -> tuple[str, list[AgentStep]]:
    steps: list[AgentStep] = []
    llm = get_llm(temperature=0.1)
    router_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]
    routed = extract_json(llm.invoke(router_messages).content)
    route = routed.get("route", "rag_answer")
    steps.append(
        AgentStep(agent="Orchestrator", action=f"Routed to: {route}", detail=routed.get("reasoning", ""))
    )

    if route == "job_search":
        query = routed.get("job_query") or message
        try:
            result = asyncio.run(call_job_search(query, limit=5))
        except MCPToolError as exc:
            steps.append(AgentStep(agent="Job Search (MCP)", action="Tool call failed", detail=str(exc)))
            return f"I couldn't reach the job search tool right now: {exc}", steps
        jobs = result.get("jobs", [])
        jobs = result.get("jobs", [])
        steps.append(
            AgentStep(
                agent="Job Search (MCP)", action="Called search_jobs tool",
                detail=f"tool_used={result.get('tool_used')}, {len(jobs)} results",
            )
        )
        if jobs:
            listing = "\n".join(f"- {j['title']} at {j['company']} ({j.get('location', '')})" for j in jobs)
            reply = f"Here are openings matching your query:\n\n{listing}"
        else:
            reply = "I couldn't find matching openings right now."
        return reply, steps

    if route == "github_analysis":
        username = routed.get("github_username", "").strip()
        if not username:
            return "Which GitHub username should I analyze?", steps
        try:
            result = asyncio.run(call_github_analysis(username))
        except MCPToolError as exc:
            steps.append(AgentStep(agent="GitHub Analysis (MCP)", action="Tool call failed", detail=str(exc)))
            return f"I couldn't reach the GitHub analysis tool right now: {exc}", steps
        result = asyncio.run(call_github_analysis(username))
        steps.append(
            AgentStep(agent="GitHub Analysis (MCP)", action="Called analyze_github_profile tool", detail=username)
        )
        if "error" in result:
            return f"Couldn't analyze that GitHub profile: {result['error']}", steps
        reply = result.get("summary", json.dumps(result))
        return reply, steps

    if route in ("skill_gap", "learning", "interview") and not profile:
        return (
            "I'd need your resume/profile first to do that accurately — "
            "please upload your resume, or tell me the skills/role directly.",
            steps,
        )

    if route == "rag_answer":
        steps.append(AgentStep(agent="RAG", action="Retrieved knowledge-base context", detail=""))
        return _rag_answer(message), steps

    # skill_gap / learning / interview without a pre-selected job: answer conversationally,
    # grounded in RAG, since these routes normally expect a JobListing from the structured UI.
    steps.append(AgentStep(agent="RAG", action="Retrieved knowledge-base context", detail=route))
    return _rag_answer(message), steps
