from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_data_agent_chat_success():
    with patch(
        "app.main.ask_data_agent",
        return_value="Alex Johnson has a delayed order."
    ):
        response = client.post(
            "/api/v1/agents/data/chat",
            json={"message": "Which orders are delayed?"}
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Alex Johnson has a delayed order."
    }


def test_data_agent_chat_empty_message():
    response = client.post(
        "/api/v1/agents/data/chat",
        json={"message": ""}
    )

    assert response.status_code == 422


def test_data_agent_chat_failure():
    with patch(
        "app.main.ask_data_agent",
        side_effect=RuntimeError("AI service unavailable")
    ):
        response = client.post(
            "/api/v1/agents/data/chat",
            json={"message": "Which orders are delayed?"}
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Data Agent request failed"