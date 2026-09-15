from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models.schemas import GitHubAnalysisRequest, GitHubAnalysisResponse
from app.mcp_tools.mcp_client import call_github_analysis, MCPToolError

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/analyze", response_model=GitHubAnalysisResponse)
async def analyze_github(req: GitHubAnalysisRequest):
    try:
        result = await call_github_analysis(req.username)
    except MCPToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return GitHubAnalysisResponse(**result)
