"""Shared state object threaded through the LangGraph workflow graph.

Every node reads what it needs off this state and writes its result back
onto it, plus appends a human-readable trace entry to `steps` so the
frontend's Agent Activity panel can show what happened and why.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentStepDict(TypedDict):
    agent: str
    action: str
    detail: str


class WorkflowState(TypedDict, total=False):
    # inputs
    profile: dict[str, Any]
    job_query: str
    location: str
    job: dict[str, Any]

    # outputs produced along the way
    match: dict[str, Any]
    skill_gap: dict[str, Any]
    roadmap: dict[str, Any]
    interview_questions: list[dict[str, Any]]

    # trace
    steps: list[AgentStepDict]


def log_step(state: WorkflowState, agent: str, action: str, detail: str = "") -> None:
    state.setdefault("steps", [])
    state["steps"].append({"agent": agent, "action": action, "detail": detail})
