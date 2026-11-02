from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.mcp_tools.mcp_client import MCPToolError, call_job_search
from app.models.schemas import JobListing, JobSearchRequest, JobSearchResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_TYPE_HINT = {
    "internship": "internship",
    "full-time": "full time entry level new grad",
}


def _matches_type(job: JobListing, job_type: str) -> bool:
    """Strict check for curated listings; web results rely on the query hint."""
    if job_type == "any" or job.source != "local":
        return True
    is_intern = "intern" in job.title.lower()
    return is_intern if job_type == "internship" else not is_intern


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(req: JobSearchRequest):
    hint = _TYPE_HINT.get(req.job_type, "")
    query = f"{req.query} {hint}".strip()
    try:
        result = await call_job_search(query, req.location or "", req.limit)
    except MCPToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    jobs = [JobListing(**j) for j in result.get("jobs", [])]
    jobs = [j for j in jobs if _matches_type(j, req.job_type)]
    return JobSearchResponse(jobs=jobs, tool_used=result.get("tool_used", "unknown"))
