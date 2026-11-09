
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from app.database import engine
from app.agents.data_agent_service import ask_data_agent

from app.services.openai_service import generate_ai_response
from app.api.supervisor import router as supervisor_router
from app.schemas import ChatRequest

load_dotenv()

# Create our FastAPI application
app = FastAPI(
    title="NexusOps AI",
    version="0.1.0"
)
app.include_router(supervisor_router)


# Health check endpoint
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "nexusops-ai"
    }


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


@app.get("/api/v1/orders")
def get_orders():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, customer_id, product, amount, status
                FROM orders
                ORDER BY id
            """)
        )

        orders = [
            {
                "id": row.id,
                "customer_id": row.customer_id,
                "product": row.product,
                "amount": float(row.amount),
                "status": row.status
            }
            for row in result
        ]

    return orders


@app.get("/api/v1/customers")
def get_customers():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, name, email
                FROM customers
                ORDER BY id
            """)
        )

        customers = [
            {
                "id": row.id,
                "name": row.name,
                "email": row.email
            }
            for row in result
        ]

    return customers


@app.get("/api/v1/tickets")
def get_tickets():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, customer_id, subject, priority, status
                FROM support_tickets
                ORDER BY id
            """)
        )

        tickets = [
            {
                "id": row.id,
                "customer_id": row.customer_id,
                "subject": row.subject,
                "priority": row.priority,
                "status": row.status
            }
            for row in result
        ]

    return tickets

@app.post("/api/v1/agents/data/chat")
def data_agent_chat(request: ChatRequest):
    try:
        answer = ask_data_agent(request.message)
        return {"answer": answer}
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Data Agent request failed"
        )
