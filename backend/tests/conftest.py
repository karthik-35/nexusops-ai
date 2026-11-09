"""Unit tests never load developer credentials or access external services."""

import os

import pytest
from openai import OpenAI
from sqlalchemy.engine import Engine

# Set before test modules import the application (and its database engine).
os.environ["PYTHON_DOTENV_DISABLED"] = "true"
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@127.0.0.1:1/test"
os.environ["OPENAI_API_KEY"] = "unit-test-placeholder"
os.environ["OPENAI_MODEL"] = "gpt-4.1-mini"


@pytest.fixture(autouse=True)
def block_external_services(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Mock OpenAI and database access in unit tests")

    monkeypatch.setattr(OpenAI, "request", blocked)
    monkeypatch.setattr(Engine, "connect", blocked)
