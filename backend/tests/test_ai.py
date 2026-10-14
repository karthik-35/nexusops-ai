
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ai_chat_success():
    # Pretend OpenAI returns a successful response
    with patch(
        "app.main.generate_ai_response",
        return_value="Hello!"
    ):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hi"}
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Hello!"


def test_ai_chat_failure():
    # Pretend OpenAI is unavailable
    with patch(
        "app.main.generate_ai_response",
        side_effect=RuntimeError("OpenAI unavailable")
    ):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hi"}
        )

    assert response.status_code == 502


def test_ai_chat_missing_key():
    # Pretend the API key is missing
    with patch(
        "app.main.generate_ai_response",
        side_effect=ValueError("Missing API key")
    ):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hi"}
        )

    assert response.status_code == 503


def test_ai_chat_empty_message():
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": ""}
    )

    assert response.status_code == 422


def test_ai_chat_too_long():
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "A" * 2001}
    )

    assert response.status_code == 422
