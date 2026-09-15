from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models.schemas import JobSearchRequest, JobSearchResponse, JobListing
from app.mcp_tools.mcp_client import call_job_search, MCPToolError

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(req: JobSearchRequest):
    try:
        result = await call_job_search(req.query, req.location or "", req.limit)
    except MCPToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    jobs = [JobListing(**j) for j in result.get("jobs", [])]
    return JobSearchResponse(jobs=jobs, tool_used=result.get("tool_used", "unknown"))
