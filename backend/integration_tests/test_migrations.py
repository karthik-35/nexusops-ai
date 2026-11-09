"""Run real migrations; routine unit tests remain independent of PostgreSQL."""

from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect, text

DATABASE = Path(__file__).resolve().parents[1] / "database"


def execute_script(connection, name):
    connection.exec_driver_sql((DATABASE / name).read_text())


def snapshot(connection):
    return {
        table: connection.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).fetchall()
        for table in ("customers", "orders", "support_tickets")
    }


def test_fresh_database_migrates_and_supports_original_seed(migration_database):
    connection, config = migration_database
    command.upgrade(config, "head")
    execute_script(connection, "seed.sql")
    assert {k: len(v) for k, v in snapshot(connection).items()} == {
        "customers": 1, "orders": 1, "support_tickets": 1,
    }
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001_business_schema"
    assert set(inspect(connection).get_table_names()) == {
        "customers", "orders", "support_tickets", "alembic_version",
    }


def test_existing_database_is_adopted_without_changing_rows(migration_database):
    connection, config = migration_database
    execute_script(connection, "schema.sql")
    execute_script(connection, "seed.sql")
    before = snapshot(connection)
    command.upgrade(config, "head")
    command.upgrade(config, "head")  # Repeated startup command is a no-op.
    assert snapshot(connection) == before
    # Preserve existing sequence behavior, not just existing rows.
    next_id = connection.scalar(text(
        "INSERT INTO customers (name, email) VALUES ('Synthetic Customer', 'migration@example.test') RETURNING id"
    ))
    assert next_id > before["customers"][-1].id


def test_schema_drift_fails_before_adoption(migration_database):
    connection, config = migration_database
    execute_script(connection, "schema.sql")
    execute_script(connection, "seed.sql")
    before = snapshot(connection)
    connection.execute(text("ALTER TABLE customers ALTER COLUMN name TYPE VARCHAR(50)"))
    with pytest.raises(RuntimeError, match="differs from the baseline"):
        command.upgrade(config, "head")
    assert snapshot(connection) == before
    assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0


def test_missing_foreign_key_is_not_silently_adopted(migration_database):
    connection, config = migration_database
    execute_script(connection, "schema.sql")
    connection.execute(text("ALTER TABLE orders DROP CONSTRAINT orders_customer_id_fkey"))
    with pytest.raises(RuntimeError, match="differs from the baseline"):
        command.upgrade(config, "head")


def test_baseline_downgrade_cannot_drop_business_data(migration_database):
    connection, config = migration_database
    command.upgrade(config, "head")
    execute_script(connection, "seed.sql")
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match="disabled to preserve business data"):
        command.downgrade(config, "base")
    assert snapshot(connection) == before


@pytest.mark.parametrize("statement", [
    "ALTER TABLE orders DROP CONSTRAINT orders_amount_check",
    "ALTER TABLE customers DROP CONSTRAINT customers_email_key",
    "ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'shipped'",
])
def test_required_constraints_and_defaults_are_validated(migration_database, statement):
    connection, config = migration_database
    execute_script(connection, "schema.sql")
    connection.execute(text(statement))
    with pytest.raises(RuntimeError, match="differs from the baseline"):
        command.upgrade(config, "head")


def test_partial_database_preserves_customers_and_creates_missing_tables(migration_database):
    connection, config = migration_database
    connection.execute(text(
        "CREATE TABLE customers (id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL, "
        "email VARCHAR(255) UNIQUE NOT NULL)"
    ))
    connection.execute(text(
        "INSERT INTO customers (name, email) VALUES ('Synthetic Customer', 'adoption@example.test')"
    ))
    before = connection.execute(text("SELECT * FROM customers")).fetchall()
    command.upgrade(config, "head")
    assert connection.execute(text("SELECT * FROM customers")).fetchall() == before
    assert connection.scalar(text("SELECT count(*) FROM orders")) == 0


def test_cross_schema_foreign_key_is_not_adopted(migration_database):
    from uuid import uuid4
    connection, config = migration_database
    execute_script(connection, "schema.sql")
    alternate = "nexusops_test_fk_" + uuid4().hex
    connection.execute(text(f'CREATE SCHEMA "{alternate}"'))
    connection.execute(text(f'CREATE TABLE "{alternate}".customers (id INTEGER PRIMARY KEY)'))
    connection.execute(text("ALTER TABLE orders DROP CONSTRAINT orders_customer_id_fkey"))
    connection.execute(text(
        f'ALTER TABLE orders ADD FOREIGN KEY (customer_id) REFERENCES "{alternate}".customers(id)'
    ))
    with pytest.raises(RuntimeError, match="differs from the baseline"):
        command.upgrade(config, "head")


def test_data_api_and_supervisor_use_real_postgres_tools(migration_database):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from fastapi.testclient import TestClient
    from app.main import app

    connection, config = migration_database
    command.upgrade(config, "head")
    execute_script(connection, "seed.sql")
    llm = MagicMock()
    llm.responses.create.side_effect = [
        SimpleNamespace(id="r1", output_text="", output=[SimpleNamespace(
            type="function_call", name="get_delayed_orders", call_id="c1", arguments="{}"
        )]),
        SimpleNamespace(output=[], output_text="Alex Johnson has a delayed order."),
    ]
    with (
        patch("app.main.engine.connect", side_effect=lambda: nullcontext(connection)),
        patch("app.agents.data_agent_service.OpenAI", return_value=llm),
    ):
        client = TestClient(app)
        assert len(client.get("/api/v1/orders").json()) == 1
        assert len(client.get("/api/v1/customers").json()) == 1
        assert len(client.get("/api/v1/tickets").json()) == 1
        response = client.post("/api/v1/agents/supervisor/chat", json={"message": "Which orders are delayed?"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    import json
    actual_tool_rows = json.loads(llm.responses.create.call_args.kwargs["input"][0]["output"])
    assert actual_tool_rows == [{
        "order_id": 1, "customer_name": "Alex Johnson", "product": "Wireless Headphones", "status": "delayed",
    }]
