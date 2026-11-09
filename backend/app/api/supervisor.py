from fastapi import APIRouter, HTTPException, Response

from app.agents.supervisor import run_supervisor
from app.schemas import ChatRequest, SupervisorResponse

router = APIRouter(prefix="/api/v1/agents/supervisor", tags=["Supervisor"])


@router.post("/chat", response_model=SupervisorResponse, responses={502: {"model": SupervisorResponse}})
def supervisor_chat(request: ChatRequest, response: Response):
    try:
        result = run_supervisor(request.message)
    except Exception:
        raise HTTPException(status_code=502, detail="Supervisor request failed") from None
    if result.status == "failed":
        response.status_code = 502
    return result
