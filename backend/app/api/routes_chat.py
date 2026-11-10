from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.orchestrator import run_chat_orchestrator
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.schemas import ChatRequest, ChatResponse
from app.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["orchestrator"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        reply = await run_chat_orchestrator(
            req.message, req.profile, current_user.id, req.session_id
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Assistant failed: {exc}") from exc
    return ChatResponse(reply=reply)
