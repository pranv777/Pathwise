from unittest.mock import AsyncMock, patch

from app.mcp_tools.mcp_client import MCPToolError

RESULT = {
    "username": "octocat",
    "public_repos": 8,
    "top_languages": ["Python", "TypeScript"],
    "notable_repos": ["hello-world", "api-server"],
    "summary": "Builds backend tools.",
}


def _mock(**kwargs):
    return patch("app.api.routes_github.call_github_analysis", new=AsyncMock(**kwargs))


def test_analyze_success(client):
    with _mock(return_value=RESULT) as call:
        r = client.post("/api/github/analyze", json={"username": "octocat"})

    assert r.status_code == 200
    assert r.json()["top_languages"] == ["Python", "TypeScript"]
    assert r.json()["notable_repos"] == ["hello-world", "api-server"]
    call.assert_awaited_once_with("octocat")


def test_error_from_the_tool_becomes_502(client):
    with _mock(return_value={"error": "GitHub user not found"}):
        r = client.post("/api/github/analyze", json={"username": "ghost"})

    assert r.status_code == 502
    assert "not found" in r.json()["detail"]


def test_tool_crash_becomes_502(client):
    with _mock(side_effect=MCPToolError("server down")):
        r = client.post("/api/github/analyze", json={"username": "octocat"})
    assert r.status_code == 502


def test_invalid_usernames_never_reach_the_tool(client):
    with _mock(return_value=RESULT) as call:
        for bad in ["bad name!", "a/b", "../etc", "", "x" * 40]:
            r = client.post("/api/github/analyze", json={"username": bad})
            assert r.status_code == 422, bad

    call.assert_not_awaited()
