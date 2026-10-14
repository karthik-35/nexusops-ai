
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.openai_service import generate_ai_response

load_dotenv()

# Create our FastAPI application
app = FastAPI(
    title="NexusOps AI",
    version="0.1.0"
)


# Health check endpoint
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "nexusops-ai"
    }


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# OpenAI chat endpoint
@app.post("/api/v1/ai/chat")
def ai_chat(request: ChatRequest):
    try:
        answer = generate_ai_response(request.message)

        return {"answer": answer}

    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured"
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="OpenAI request failed"
        )
