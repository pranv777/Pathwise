"""MCP server exposing an `analyze_github_profile` tool.

Uses the public GitHub REST API. Works unauthenticated (60 req/hr limit);
set GITHUB_TOKEN in .env for higher limits.

Run standalone for debugging:  python -m app.mcp_tools.github_server
"""

import json
import re
from collections import Counter

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("github-analysis")

API_BASE = "https://api.github.com"
_USERNAME_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


@mcp.tool()
def analyze_github_profile(username: str) -> str:
    """Fetch a GitHub user's public repositories and summarize their
    top languages and most notable (highest-starred) repos. Returns JSON
    with username, public_repos, top_languages, notable_repos, summary."""
    username = username.strip()
    if not _USERNAME_RE.fullmatch(username):
        return json.dumps({"error": f"'{username}' is not a valid GitHub username"})
    try:
        with httpx.Client(timeout=15.0, headers=_headers()) as client:
            user_resp = client.get(f"{API_BASE}/users/{username}")
            user_resp.raise_for_status()
            user = user_resp.json()

            repos_resp = client.get(
                f"{API_BASE}/users/{username}/repos",
                params={"per_page": 100, "sort": "updated"},
            )
            repos_resp.raise_for_status()
            repos = repos_resp.json()

        lang_counts: Counter[str] = Counter()
        for repo in repos:
            if repo.get("language"):
                lang_counts[repo["language"]] += 1

        notable = sorted(
            repos, key=lambda r: r.get("stargazers_count", 0), reverse=True
        )[:5]
        notable_names = [
            f"{r['name']} ({r.get('stargazers_count', 0)}★, {r.get('language') or 'n/a'})"
            for r in notable
        ]

        top_languages = [lang for lang, _ in lang_counts.most_common(6)]

        result = {
            "username": username,
            "public_repos": user.get("public_repos", len(repos)),
            "top_languages": top_languages,
            "notable_repos": notable_names,
            "summary": (
                f"{username} has {user.get('public_repos', len(repos))} public repos, "
                f"primarily in {', '.join(top_languages[:3]) or 'no detected languages'}. "
                f"Bio: {user.get('bio') or 'n/a'}."
            ),
        }
        return json.dumps(result)
    except httpx.HTTPStatusError as exc:
        return json.dumps(
            {
                "error": f"GitHub API error {exc.response.status_code} for user '{username}'"
            }
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
