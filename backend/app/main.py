import os

from dotenv import load_dotenv
from google import genai
from fastapi import HTTPException
from pydantic import BaseModel

load_dotenv()

from fastapi import FastAPI

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
    message: str


@app.post("/api/v1/ai/chat")
def ai_chat(request: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured"
        )

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=request.message
        )

        return {"answer": response.text}

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Gemini request failed"
        )
