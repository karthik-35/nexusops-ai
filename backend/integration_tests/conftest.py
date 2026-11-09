"""Opt-in PostgreSQL tests isolated in schemas rolled back after every test."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_database():
    if os.getenv("NEXUSOPS_RUN_DB_TESTS") != "1":
        pytest.skip("Set NEXUSOPS_RUN_DB_TESTS=1 to run isolated PostgreSQL tests")
    load_dotenv(BACKEND / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL is required for integration tests")
    engine = create_engine(url, hide_parameters=True)
    schema = "nexusops_test_" + uuid4().hex
    try:
        try:
            connection = engine.connect()
        except Exception:
            # Pytest's long tracebacks can display DBAPI connection arguments.
            pytest.fail("Cannot connect to PostgreSQL; check Docker and local configuration", pytrace=False)
        with connection:
            transaction = connection.begin()
            try:
                # Identifiers are generated internally from UUIDs, never user input.
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                config = Config(str(BACKEND / "alembic.ini"))
                config.attributes["connection"] = connection
                yield connection, config
            finally:
                transaction.rollback()  # Removes only this transaction's test schema.
    finally:
        engine.dispose()
