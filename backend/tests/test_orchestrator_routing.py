"""Orchestrator tests: the LLM router, each route's agent/tool dispatch,
conversation memory and the LangGraph pipeline.

Every LLM, MCP and vector-store call is mocked, so these run offline.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from app.agents import memory, orchestrator
from app.agents.orchestrator import run_chat_orchestrator
from app.mcp_tools.mcp_client import MCPToolError
from app.models.llm_outputs import RouteOut
from app.models.schemas import (
    InterviewGenerateResponse,
    InterviewQuestion,
    JobMatchResponse,
    LearningResource,
    LearningRoadmapResponse,
    SkillGapResponse,
    StudentProfile,
)

PROFILE = StudentProfile(name="Asha", skills=["Python"])

ROUTE_DEFAULTS = {
    "route": "rag_answer",
    "reasoning": "because",
    "job_query": "",
    "github_username": "",
    "role": "",
    "skills": [],
}


@pytest.fixture(autouse=True)
def _clean_memory():
    memory._sessions.clear()
    yield
    memory._sessions.clear()


@pytest.fixture()
def set_route(monkeypatch):
    """Make the router LLM return a chosen RouteOut; returns the mock."""

    def _set(**fields):
        out = RouteOut(**{**ROUTE_DEFAULTS, **fields})
        mock = MagicMock(return_value=out)
        monkeypatch.setattr(orchestrator, "invoke_json", mock)
        return mock

    return _set


def chat(message="hello", profile=PROFILE, user_id=1, session_id="s1"):
    return asyncio.run(run_chat_orchestrator(message, profile, user_id, session_id))


# ---------------------------------------------------------------- routing


def test_router_decision_is_recorded_as_the_first_step(set_route, monkeypatch):
    set_route(route="rag_answer", reasoning="general question")
    monkeypatch.setattr(orchestrator, "_rag_answer", AsyncMock(return_value="ok"))

    _, steps = chat("how do I prepare?")

    assert steps[0].agent == "Orchestrator"
    assert steps[0].action == "Routed to: rag_answer"
    assert steps[0].detail == "general question"


def test_unknown_route_falls_back_to_rag_answer(set_route, monkeypatch):
    set_route(route="make_coffee")
    rag = AsyncMock(return_value="fallback answer")
    monkeypatch.setattr(orchestrator, "_rag_answer", rag)

    reply, steps = chat("brew something")

    assert reply == "fallback answer"
    assert steps[0].action == "Routed to: rag_answer"
    rag.assert_awaited_once()


def test_rag_answer_route_passes_message_user_and_history(set_route, monkeypatch):
    set_route(route="rag_answer")
    rag = AsyncMock(return_value="general advice")
    monkeypatch.setattr(orchestrator, "_rag_answer", rag)

    reply, steps = chat("how do I prepare?", user_id=7)

    assert reply == "general advice"
    rag.assert_awaited_once_with("how do I prepare?", 7, [])
    assert steps[-1].agent == "RAG"
    assert steps[-1].detail == "rag_answer"


# ------------------------------------------------------------ job search


def test_job_search_route_calls_the_mcp_tool(set_route, monkeypatch):
    set_route(route="job_search", job_query="python intern")
    search = AsyncMock(
        return_value={
            "jobs": [{"title": "SWE Intern", "company": "Acme", "location": "Pune"}],
            "tool_used": "local_fallback",
        }
    )
    monkeypatch.setattr(orchestrator, "call_job_search", search)

    reply, steps = chat("find me python internships")

    search.assert_awaited_once_with("python intern", limit=5)
    assert "SWE Intern at Acme (Pune)" in reply
    assert steps[1].agent == "Job Search (MCP)"
    assert "local_fallback" in steps[1].detail
    assert "1 results" in steps[1].detail


def test_job_search_falls_back_to_the_raw_message(set_route, monkeypatch):
    set_route(route="job_search", job_query="")
    search = AsyncMock(return_value={"jobs": [], "tool_used": "local_fallback"})
    monkeypatch.setattr(orchestrator, "call_job_search", search)

    chat("any openings in fintech")

    search.assert_awaited_once_with("any openings in fintech", limit=5)


def test_job_search_with_no_results(set_route, monkeypatch):
    set_route(route="job_search", job_query="underwater basket weaving")
    monkeypatch.setattr(
        orchestrator,
        "call_job_search",
        AsyncMock(return_value={"jobs": [], "tool_used": "local_fallback"}),
    )

    reply, _ = chat("find jobs")

    assert "couldn't find" in reply


def test_job_search_tool_failure_is_reported(set_route, monkeypatch):
    set_route(route="job_search", job_query="python")
    monkeypatch.setattr(
        orchestrator,
        "call_job_search",
        AsyncMock(side_effect=MCPToolError("server down")),
    )

    reply, steps = chat("find jobs")

    assert "couldn't reach the job search tool" in reply
    assert "server down" in reply
    assert steps[-1].action == "Tool call failed"


# ---------------------------------------------------------------- GitHub


def test_github_route_strips_the_username_and_returns_the_summary(
    set_route, monkeypatch
):
    set_route(route="github_analysis", github_username="  octocat ")
    tool = AsyncMock(return_value={"summary": "Builds backend tools."})
    monkeypatch.setattr(orchestrator, "call_github_analysis", tool)

    reply, steps = chat("analyze github user octocat")

    tool.assert_awaited_once_with("octocat")
    assert reply == "Builds backend tools."
    assert steps[-1].agent == "GitHub Analysis (MCP)"
    assert steps[-1].detail == "octocat"


def test_github_route_asks_when_no_username_was_found(set_route, monkeypatch):
    set_route(route="github_analysis", github_username="   ")
    tool = AsyncMock()
    monkeypatch.setattr(orchestrator, "call_github_analysis", tool)

    reply, _ = chat("analyze my github")

    assert "Which GitHub username" in reply
    tool.assert_not_awaited()


def test_github_route_reports_tool_errors(set_route, monkeypatch):
    set_route(route="github_analysis", github_username="ghost")
    monkeypatch.setattr(
        orchestrator,
        "call_github_analysis",
        AsyncMock(return_value={"error": "user not found"}),
    )

    reply, _ = chat("analyze ghost")

    assert "Couldn't analyze that GitHub profile" in reply
    assert "user not found" in reply


def test_github_route_reports_unreachable_tool(set_route, monkeypatch):
    set_route(route="github_analysis", github_username="octocat")
    monkeypatch.setattr(
        orchestrator,
        "call_github_analysis",
        AsyncMock(side_effect=MCPToolError("timeout")),
    )

    reply, steps = chat("analyze octocat")

    assert "couldn't reach the GitHub analysis tool" in reply
    assert steps[-1].action == "Tool call failed"


# ------------------------------------------------------------- skill gap


def test_skill_gap_route_needs_a_resume(set_route, monkeypatch):
    set_route(route="skill_gap", role="Backend Intern")
    agent = MagicMock()
    monkeypatch.setattr(orchestrator, "run_skill_gap_agent", agent)

    reply, _ = chat("what am I missing?", profile=None)

    assert "Upload your resume first" in reply
    agent.assert_not_called()


def test_skill_gap_route_ranks_the_missing_skills(set_route, monkeypatch):
    set_route(route="skill_gap", role="Backend Intern")
    monkeypatch.setattr(
        orchestrator,
        "_role_as_job",
        AsyncMock(return_value=SimpleNamespace(title="Backend Intern")),
    )
    agent = MagicMock(
        return_value=SkillGapResponse(
            missing_skills=["Docker", "SQL"],
            priority_order=["Docker", "SQL"],
            explanation="Docker comes first.",
        )
    )
    monkeypatch.setattr(orchestrator, "run_skill_gap_agent", agent)

    reply, steps = chat("what am I missing for backend intern?")

    assert "For **Backend Intern**" in reply
    assert "1. Docker" in reply
    assert "2. SQL" in reply
    assert "Docker comes first." in reply
    assert steps[-1].agent == "Skill Gap Agent"
    assert "2 gaps" in steps[-1].detail


def test_skill_gap_route_uses_the_message_when_no_role_was_extracted(
    set_route, monkeypatch
):
    set_route(route="skill_gap", role="")
    role_as_job = AsyncMock(return_value=SimpleNamespace(title="x"))
    monkeypatch.setattr(orchestrator, "_role_as_job", role_as_job)
    monkeypatch.setattr(
        orchestrator,
        "run_skill_gap_agent",
        MagicMock(
            return_value=SkillGapResponse(
                missing_skills=[], priority_order=[], explanation="none"
            )
        ),
    )

    chat("gaps for data analyst")

    role_as_job.assert_awaited_once_with("gaps for data analyst")


# -------------------------------------------------------------- learning


def test_learning_route_builds_a_roadmap_from_the_skills(set_route, monkeypatch):
    set_route(route="learning", skills=["Docker", ""])
    agent = MagicMock(
        return_value=LearningRoadmapResponse(
            roadmap=[
                LearningResource(
                    skill="Docker", resources=["Docker docs"], estimated_weeks=2
                )
            ],
            total_estimated_weeks=2,
        )
    )
    monkeypatch.setattr(orchestrator, "run_learning_agent", agent)

    reply, steps = chat("how do I learn docker?")

    agent.assert_called_once_with(["Docker"])  # blank skills are dropped
    assert "**1. Docker** (~2w)" in reply
    assert "- Docker docs" in reply
    assert "_Total: ~2 weeks_" in reply
    assert steps[-1].agent == "Learning Recommendation Agent"


def test_learning_route_without_skills_falls_back_to_rag(set_route, monkeypatch):
    set_route(route="learning", skills=[])
    rag = AsyncMock(return_value="general learning advice")
    monkeypatch.setattr(orchestrator, "_rag_answer", rag)

    reply, steps = chat("how should I study?")

    assert reply == "general learning advice"
    assert steps[-1].agent == "RAG"
    assert steps[-1].detail == "learning"


# ------------------------------------------------------------- interview


def test_interview_route_formats_the_questions(set_route, monkeypatch):
    set_route(route="interview", role="Backend Intern")
    agent = MagicMock(
        return_value=InterviewGenerateResponse(
            questions=[
                InterviewQuestion(
                    question="What is REST?",
                    category="technical",
                    answer="An architectural style.",
                )
            ]
        )
    )
    monkeypatch.setattr(orchestrator, "run_interview_generate", agent)

    reply, steps = chat("interview questions for backend intern")

    agent.assert_called_once_with("Backend Intern", PROFILE, 5)
    assert "**1. What is REST?** _(technical)_" in reply
    assert "An architectural style." in reply
    assert steps[-1].agent == "Interview Agent"


def test_interview_route_works_without_a_profile(set_route, monkeypatch):
    set_route(route="interview", role="")
    agent = MagicMock(return_value=InterviewGenerateResponse(questions=[]))
    monkeypatch.setattr(orchestrator, "run_interview_generate", agent)

    chat("practise for data analyst", profile=None)

    agent.assert_called_once_with("practise for data analyst", None, 5)


# ---------------------------------------------------------------- memory


def test_conversation_history_is_sent_to_the_router(set_route, monkeypatch):
    router = set_route(route="rag_answer")
    monkeypatch.setattr(
        orchestrator, "_rag_answer", AsyncMock(return_value="first answer")
    )

    chat("first question")
    chat("second question")

    first = router.call_args_list[0].args[1]
    second = router.call_args_list[1].args[1]
    assert len(first) == 2  # system prompt + new message
    assert len(second) == 4  # system prompt + 1 remembered turn + new message
    assert second[1].content == "first question"
    assert second[2].content == "first answer"


def test_memory_is_separate_per_user_and_session(set_route, monkeypatch):
    router = set_route(route="rag_answer")
    monkeypatch.setattr(orchestrator, "_rag_answer", AsyncMock(return_value="a"))

    chat("hello", user_id=1, session_id="s1")
    chat("hello again", user_id=2, session_id="s1")  # other user
    chat("hello again", user_id=1, session_id="s2")  # other session

    assert len(router.call_args_list[1].args[1]) == 2
    assert len(router.call_args_list[2].args[1]) == 2


# ------------------------------------------------------------ RAG helper


def _fake_llm(answer="the answer"):
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=SimpleNamespace(content=answer))
    return llm


def test_rag_answer_uses_shared_and_resume_context(monkeypatch):
    search = MagicMock(
        side_effect=[
            [(Document(page_content="shared tip"), 0.9)],
            [(Document(page_content="my resume line"), 0.8)],
        ]
    )
    llm = _fake_llm()
    monkeypatch.setattr(orchestrator, "search", search)
    monkeypatch.setattr(orchestrator, "get_llm", MagicMock(return_value=llm))

    answer = asyncio.run(orchestrator._rag_answer("how to prepare?", 7, []))

    assert answer == "the answer"
    assert search.call_args_list[0].args == ("how to prepare?", 4)
    assert search.call_args_list[1].args == ("how to prepare?", 2, "resume", 7)
    prompt = llm.ainvoke.call_args.args[0][-1].content
    assert "shared tip" in prompt
    assert "my resume line" in prompt


def test_rag_answer_skips_resume_search_without_a_user(monkeypatch):
    search = MagicMock(return_value=[(Document(page_content="shared tip"), 0.9)])
    llm = _fake_llm()
    monkeypatch.setattr(orchestrator, "search", search)
    monkeypatch.setattr(orchestrator, "get_llm", MagicMock(return_value=llm))

    asyncio.run(orchestrator._rag_answer("question", None, []))

    assert search.call_count == 1
    assert (
        "CANDIDATE RESUME EXCERPTS:\nnone" in llm.ainvoke.call_args.args[0][-1].content
    )


def test_role_as_job_builds_a_listing_from_templates(monkeypatch):
    docs = [
        (Document(page_content="Needs Python"), 0.9),
        (Document(page_content="Needs SQL"), 0.8),
    ]
    monkeypatch.setattr(orchestrator, "search", MagicMock(return_value=docs))

    job = asyncio.run(orchestrator._role_as_job("Backend Intern"))

    assert job.id == "chat-role"
    assert job.title == "Backend Intern"
    assert job.description == "Needs Python\nNeeds SQL"


def test_role_as_job_without_templates_uses_a_default(monkeypatch):
    monkeypatch.setattr(orchestrator, "search", MagicMock(return_value=[]))

    job = asyncio.run(orchestrator._role_as_job("Data Analyst"))

    assert job.description == "Data Analyst role"


# ---------------------------------------------------- LangGraph pipeline

JOB = {
    "id": "j1",
    "title": "Backend Intern",
    "company": "Acme",
    "location": "Pune",
    "description": "Python and Docker",
    "url": "",
    "source": "local",
}


@pytest.fixture()
def agents(monkeypatch):
    mocks = {
        "call_job_search": AsyncMock(
            return_value={"jobs": [JOB], "tool_used": "local_fallback"}
        ),
        "run_job_matching_agent": MagicMock(
            return_value=JobMatchResponse(
                match_score=77,
                matched_skills=["Python"],
                missing_skills=["Docker"],
                rationale="ok",
            )
        ),
        "run_skill_gap_agent": MagicMock(
            return_value=SkillGapResponse(
                missing_skills=["Docker"],
                priority_order=["Docker"],
                explanation="Docker first",
            )
        ),
        "run_learning_agent": MagicMock(
            return_value=LearningRoadmapResponse(
                roadmap=[
                    LearningResource(
                        skill="Docker", resources=["Docker docs"], estimated_weeks=2
                    )
                ],
                total_estimated_weeks=2,
            )
        ),
        "run_interview_generate": MagicMock(
            return_value=InterviewGenerateResponse(
                questions=[
                    InterviewQuestion(question="What is Docker?", category="technical")
                ]
            )
        ),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(orchestrator, name, mock)
    return mocks
