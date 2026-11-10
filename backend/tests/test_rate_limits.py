from unittest.mock import patch

from app.agents.job_matching_agent import run_job_matching_agent  # noqa: F401
from app.models.schemas import JobMatchResponse


def test_matching_route_is_rate_limited(client):
    body = {
        "profile": {"name": "A", "skills": []},
        "job": {"id": "job-1", "title": "Dev", "company": "X", "description": "d"},
    }
    match = JobMatchResponse(
        match_score=50, matched_skills=[], missing_skills=[], rationale="ok"
    )
    with patch("app.api.routes_matching.run_job_matching_agent", return_value=match):
        statuses = [
            client.post("/api/matching/score", json=body).status_code for _ in range(17)
        ]
    assert 429 in statuses
