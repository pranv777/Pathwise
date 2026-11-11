import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.mcp_tools import github_server, job_search_server


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("bad", request=MagicMock(), response=resp)
    return resp


def _client(*responses):
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.side_effect = list(responses)
    return client


def test_github_headers_include_the_token_only_when_set(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "")
    assert "Authorization" not in github_server._headers()
    monkeypatch.setattr(settings, "github_token", "tok")
    assert github_server._headers()["Authorization"] == "Bearer tok"


@pytest.mark.parametrize("name", ["bad name", "", "a" * 40, "x/../y"])
def test_github_rejects_invalid_usernames(name):
    out = json.loads(github_server.analyze_github_profile(name))
    assert "not a valid GitHub username" in out["error"]


def test_github_summarises_languages_and_notable_repos():
    repos = [
        {"name": "a", "language": "Python", "stargazers_count": 5},
        {"name": "b", "language": "Python", "stargazers_count": 50},
        {"name": "c", "language": None, "stargazers_count": 1},
    ]
    user = {"public_repos": 3, "bio": "hi"}
    with patch(
        "app.mcp_tools.github_server.httpx.Client",
        return_value=_client(_response(user), _response(repos)),
    ):
        out = json.loads(github_server.analyze_github_profile("  octo  "))
    assert out["username"] == "octo"
    assert out["top_languages"] == ["Python"]
    assert out["notable_repos"][0] == "b (50★, Python)"
    assert out["notable_repos"][-1] == "c (1★, n/a)"
    assert "Bio: hi" in out["summary"]


def test_github_summary_without_languages_or_bio():
    with patch(
        "app.mcp_tools.github_server.httpx.Client",
        return_value=_client(_response({}), _response([])),
    ):
        out = json.loads(github_server.analyze_github_profile("octo"))
    assert out["public_repos"] == 0
    assert "no detected languages" in out["summary"] and "Bio: n/a" in out["summary"]


def test_github_reports_http_errors():
    with patch(
        "app.mcp_tools.github_server.httpx.Client",
        return_value=_client(_response({}, status=404)),
    ):
        out = json.loads(github_server.analyze_github_profile("ghost"))
    assert out["error"] == "GitHub API error 404 for user 'ghost'"


def test_github_reports_unexpected_errors():
    with patch("app.mcp_tools.github_server.httpx.Client", side_effect=RuntimeError("offline")):
        out = json.loads(github_server.analyze_github_profile("octo"))
    assert out["error"] == "offline"


@pytest.fixture()
def jobs_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    jobs = [
        {"id": "1", "title": "Python Intern", "description": "django", "location": "Pune"},
        {"id": "2", "title": "Java Dev", "description": "spring", "location": "Delhi"},
    ]
    (tmp_path / "sample_jobs.json").write_text(json.dumps(jobs))
    return jobs


def test_local_jobs_are_empty_without_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    assert job_search_server._local_jobs() == []
    assert job_search_server._search_local("python", None, 5) == []


def test_local_search_scores_keywords_and_location(jobs_file):
    hits = job_search_server._search_local("python", "pune", 5)
    assert [j["id"] for j in hits] == ["1"]
    assert hits[0]["source"] == "local"


def test_local_search_returns_everything_for_an_empty_query(jobs_file):
    assert len(job_search_server._search_local("", None, 5)) == 2


def test_local_search_falls_back_to_the_first_jobs_when_nothing_matches(jobs_file):
    hits = job_search_server._search_local("cobol", None, 1)
    assert [j["id"] for j in hits] == ["1"]


def test_stable_id_is_deterministic():
    assert job_search_server._stable_id("u") == job_search_server._stable_id("u")
    assert len(job_search_server._stable_id("u")) == 10


def _tavily(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


def test_tavily_results_are_mapped_to_listings(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "key")
    payload = {"results": [{"url": "https://x.test/1", "title": "T", "content": "c" * 2000}]}
    with patch("app.mcp_tools.job_search_server.httpx.post", return_value=_tavily(payload)) as post:
        jobs = job_search_server._search_tavily("python", "Pune", 3)
    assert post.call_args.kwargs["json"]["query"] == "python job openings in Pune"
    assert jobs[0]["id"].startswith("web-") and jobs[0]["source"] == "web"
    assert len(jobs[0]["description"]) == 1000 and jobs[0]["location"] == "Pune"


def test_search_jobs_prefers_tavily_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "key")
    payload = {"results": [{"url": "https://x.test/1"}]}
    with patch("app.mcp_tools.job_search_server.httpx.post", return_value=_tavily(payload)):
        out = json.loads(job_search_server.search_jobs("python"))
    assert out["tool_used"] == "tavily_web_search"
    assert out["jobs"][0]["title"] == "python"


def test_search_jobs_falls_back_when_tavily_is_empty(monkeypatch, jobs_file):
    monkeypatch.setattr(settings, "tavily_api_key", "key")
    with patch("app.mcp_tools.job_search_server.httpx.post", return_value=_tavily({"results": []})):
        out = json.loads(job_search_server.search_jobs("python"))
    assert out["tool_used"] == "local_fallback"


def test_search_jobs_reports_tavily_errors_and_still_returns_jobs(monkeypatch, jobs_file):
    monkeypatch.setattr(settings, "tavily_api_key", "key")
    with patch("app.mcp_tools.job_search_server.httpx.post", side_effect=RuntimeError("down")):
        out = json.loads(job_search_server.search_jobs("python", "Pune"))
    assert out["tool_used"] == "local_fallback_after_error"
    assert out["error"] == "down" and out["jobs"]


def test_search_jobs_without_a_key_uses_local_listings(monkeypatch, jobs_file):
    monkeypatch.setattr(settings, "tavily_api_key", "")
    out = json.loads(job_search_server.search_jobs("java"))
    assert out["tool_used"] == "local_fallback"
    assert out["jobs"][0]["id"] == "2"
