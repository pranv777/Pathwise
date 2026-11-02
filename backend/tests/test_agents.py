from unittest.mock import patch

import pytest

from app.agents.job_matching_agent import run_job_matching_agent
from app.agents.resume_agent import run_resume_agent
from app.config import settings
from app.models.llm_outputs import JobMatchOut, ResumeOut
from app.models.schemas import JobListing, StudentProfile
from app.utils import structured


@pytest.fixture(autouse=True)
def _reset_stats(monkeypatch):
    monkeypatch.setattr(settings, "llm_output_mode", "structured")
    structured.stats.clear()
    yield
    structured.stats.clear()


@patch("app.agents.resume_agent.invoke_json")
def test_resume_agent_maps_output(mock_invoke):
    mock_invoke.return_value = ResumeOut(
        name="Jane Doe",
        email="jane@example.com",
        skills=["Python", "FastAPI"],
        education=[],
        projects=["Built a chatbot"],
        experience=[],
        certifications=[],
    )
    profile = run_resume_agent("resume text")
    assert profile.name == "Jane Doe" and "Python" in profile.skills


@patch("app.agents.job_matching_agent.search", return_value=[])
@patch("app.agents.job_matching_agent.invoke_json")
def test_match_score_is_clamped(mock_invoke, _search):
    mock_invoke.return_value = JobMatchOut(
        match_score=140, matched_skills=["Python"], missing_skills=[], rationale="x"
    )
    job = JobListing(id="1", title="Intern", company="Acme", description="Python")
    result = run_job_matching_agent(StudentProfile(skills=["Python"]), job)
    assert result.match_score == 100


def test_invoke_json_retries_then_succeeds():
    good = JobMatchOut(
        match_score=70, matched_skills=[], missing_skills=[], rationale="ok"
    )
    with patch.object(
        structured,
        "_call_structured",
        side_effect=[structured.StructuredOutputError("none"), good],
    ):
        out = structured.invoke_json(JobMatchOut, [])
    assert out == good
    assert structured.stats["retries"] == 1
    assert structured.stats["first_attempt_failures"] == 1
    assert structured.stats["final_failures"] == 0


def test_legacy_mode_has_no_retries(monkeypatch):
    monkeypatch.setattr(settings, "llm_output_mode", "legacy")
    with (
        patch.object(
            structured,
            "_call_legacy",
            side_effect=structured.StructuredOutputError("bad"),
        ),
        pytest.raises(structured.StructuredOutputError),
    ):
        structured.invoke_json(JobMatchOut, [])
    assert structured.stats["retries"] == 0
    assert structured.stats["final_failures"] == 1
