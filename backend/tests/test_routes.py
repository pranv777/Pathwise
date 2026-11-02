from unittest.mock import patch

from app.models.schemas import JobMatchResponse


def test_matching_route_success(client, auth_headers):
    with patch("app.api.routes_matching.run_job_matching_agent") as mock_agent:
        mock_agent.return_value = JobMatchResponse(
            match_score=80, matched_skills=["Python"], missing_skills=[], rationale="ok"
        )
        payload = {
            "profile": {"skills": ["Python"], "projects": [], "experience": []},
            "job": {
                "id": "1",
                "title": "Intern",
                "company": "Acme",
                "description": "Python role",
            },
        }
        r = client.post("/api/matching/score", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["match_score"] == 80


def test_matching_route_handles_agent_failure(client, auth_headers):
    with patch(
        "app.api.routes_matching.run_job_matching_agent",
        side_effect=Exception("LLM down"),
    ):
        payload = {
            "profile": {"skills": [], "projects": [], "experience": []},
            "job": {
                "id": "1",
                "title": "Intern",
                "company": "Acme",
                "description": "desc",
            },
        }
        r = client.post("/api/matching/score", json=payload, headers=auth_headers)
        assert r.status_code == 502
