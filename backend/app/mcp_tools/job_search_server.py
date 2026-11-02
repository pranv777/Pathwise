"""MCP server exposing a `search_jobs` tool.

Uses the Tavily web-search API when TAVILY_API_KEY is configured, otherwise
falls back to a curated local listings file so the whole project still runs
end-to-end without any paid keys.

Run standalone for debugging:  python -m app.mcp_tools.job_search_server
"""

import hashlib
import json
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("job-search")


def _local_jobs() -> list[dict]:
    path = Path(settings.knowledge_base_dir) / "sample_jobs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _search_local(query: str, location: str | None, limit: int) -> list[dict]:
    query_lower = query.lower()
    jobs = _local_jobs()
    scored = []
    for job in jobs:
        haystack = f"{job['title']} {job['description']}".lower()
        score = sum(1 for word in query_lower.split() if word in haystack)
        if location and location.lower() in job.get("location", "").lower():
            score += 2
        if score > 0 or not query_lower:
            scored.append((score, job))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [job for _, job in scored[:limit]] or jobs[:limit]
    for job in results:
        job["source"] = "local"
    return results


def _stable_id(url: str) -> str:
    """Deterministic across processes (built-in hash() is salted per run), so
    history de-duplication keeps working for the same web listing."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def _search_tavily(query: str, location: str | None, limit: int) -> list[dict]:
    full_query = f"{query} job openings"
    if location:
        full_query += f" in {location}"
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": settings.tavily_api_key,
            "query": full_query,
            "search_depth": "basic",
            "max_results": limit,
            "include_answer": False,
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for item in data.get("results", [])[:limit]:
        url = item.get("url", "")
        jobs.append(
            {
                "id": f"web-{_stable_id(url)}",
                "title": item.get("title", query),
                "company": "See listing",
                "location": location or "",
                "description": item.get("content", "")[:1000],
                "url": url,
                "source": "web",
            }
        )
    return jobs


@mcp.tool()
def search_jobs(query: str, location: str = "", limit: int = 5) -> str:
    """Search for job/internship openings matching a query and optional
    location. Returns a JSON array of job listings with title, company,
    location, description, url, and source ("web" or "local")."""
    try:
        if settings.tavily_api_key:
            jobs = _search_tavily(query, location or None, limit)
            if jobs:
                return json.dumps({"jobs": jobs, "tool_used": "tavily_web_search"})
        jobs = _search_local(query, location or None, limit)
        return json.dumps({"jobs": jobs, "tool_used": "local_fallback"})
    except Exception as exc:  # noqa: BLE001
        jobs = _search_local(query, location or None, limit)
        return json.dumps(
            {"jobs": jobs, "tool_used": "local_fallback_after_error", "error": str(exc)}
        )


if __name__ == "__main__":
    mcp.run(transport="stdio")
