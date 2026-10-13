
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
