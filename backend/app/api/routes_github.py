from fastapi import APIRouter, HTTPException, Request

from app.mcp_tools.mcp_client import MCPToolError, call_github_analysis
from app.models.schemas import GitHubAnalysisRequest, GitHubAnalysisResponse
from app.rate_limit import limiter

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/analyze", response_model=GitHubAnalysisResponse)
@limiter.limit("10/minute")
async def analyze_github(request: Request, req: GitHubAnalysisRequest):
    try:
        result = await call_github_analysis(req.username)
    except MCPToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return GitHubAnalysisResponse(**result)
