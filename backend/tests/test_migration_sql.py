from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_baseline_offline_sql_is_create_only():
    output = StringIO()
    config = Config(
        str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output
    )
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    for table in ("customers", "orders", "support_tickets", "alembic_version"):
        assert f"CREATE TABLE {table}" in sql
    assert "FOREIGN KEY(customer_id) REFERENCES customers (id)" in sql
    assert "CHECK (amount >= 0)" in sql
    assert "DROP " not in sql
    assert "TRUNCATE " not in sql
    assert "0001_business_schema" in sql
