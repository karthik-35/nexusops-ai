
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ai_chat_success():
    # Pretend Gemini returns "Hello!"
    fake_response = MagicMock()
    fake_response.text = "Hello!"

    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "fake-test-key"}
    ):
        with patch("app.main.genai.Client") as mock_client:
            mock_client.return_value.models.generate_content.return_value = fake_response

            response = client.post(
                "/api/v1/ai/chat",
                json={"message": "Hi"}
            )

    assert response.status_code == 200
    assert response.json()["answer"] == "Hello!"


def test_ai_chat_failure():
    # Pretend Gemini is unavailable
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "fake-test-key"}
    ):
        with patch("app.main.genai.Client") as mock_client:
            mock_client.return_value.models.generate_content.side_effect = Exception(
                "Gemini unavailable"
            )

            response = client.post(
                "/api/v1/ai/chat",
                json={"message": "Hi"}
            )

    assert response.status_code == 502


def test_ai_chat_missing_key():
    # Pretend no API key exists
    with patch.dict("os.environ", {}, clear=True):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hi"}
        )

    assert response.status_code == 503
