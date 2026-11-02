from unittest.mock import AsyncMock, patch

from app.mcp_tools.mcp_client import MCPToolError

LOCAL_INTERN = {
    "id": "local-1",
    "title": "Software Engineer Intern",
    "company": "A",
    "description": "d",
    "source": "local",
}
LOCAL_FULL_TIME = {
    "id": "local-2",
    "title": "Full Stack Developer - New Grad",
    "company": "B",
    "description": "d",
    "source": "local",
}
WEB = {
    "id": "web-1",
    "title": "Backend Developer",
    "company": "C",
    "description": "d",
    "source": "web",
}


def _mock_search(jobs=None, **kwargs):
    result = {"jobs": jobs or [LOCAL_INTERN, LOCAL_FULL_TIME, WEB], "tool_used": "test"}
    return patch(
        "app.api.routes_jobs.call_job_search",
        new=AsyncMock(return_value=result, **kwargs),
    )


def _ids(response):
    return [j["id"] for j in response.json()["jobs"]]


def test_any_type_returns_everything_and_leaves_the_query_alone(client):
    with _mock_search() as search:
        r = client.post("/api/jobs/search", json={"query": "python", "limit": 5})

    assert r.status_code == 200
    assert _ids(r) == ["local-1", "local-2", "web-1"]
    search.assert_awaited_once_with("python", "", 5)


def test_internship_filter_adds_a_hint_and_filters_local_listings(client):
    with _mock_search() as search:
        r = client.post(
            "/api/jobs/search",
            json={"query": "python", "job_type": "internship"},
        )

    assert search.await_args.args[0] == "python internship"
    # local non-internships are dropped; web results are kept (titles are unreliable)
    assert _ids(r) == ["local-1", "web-1"]


def test_full_time_filter_adds_a_hint_and_drops_local_internships(client):
    with _mock_search() as search:
        r = client.post(
            "/api/jobs/search",
            json={"query": "python", "job_type": "full-time"},
        )

    assert "full time" in search.await_args.args[0]
    assert _ids(r) == ["local-2", "web-1"]


def test_location_is_passed_through(client):
    with _mock_search() as search:
        client.post("/api/jobs/search", json={"query": "python", "location": "Pune"})
    assert search.await_args.args[1] == "Pune"


def test_invalid_job_type_is_rejected(client):
    r = client.post("/api/jobs/search", json={"query": "python", "job_type": "gig"})
    assert r.status_code == 422


def test_search_input_limits(client):
    assert client.post("/api/jobs/search", json={"query": ""}).status_code == 422
    assert client.post("/api/jobs/search", json={"query": "q" * 201}).status_code == 422
    assert (
        client.post("/api/jobs/search", json={"query": "q", "limit": 21}).status_code
        == 422
    )


def test_tool_failure_returns_502(client):
    with patch(
        "app.api.routes_jobs.call_job_search",
        new=AsyncMock(side_effect=MCPToolError("server down")),
    ):
        r = client.post("/api/jobs/search", json={"query": "python"})
    assert r.status_code == 502
