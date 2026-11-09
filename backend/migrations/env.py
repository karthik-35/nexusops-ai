"""Migration connections use the same local configuration as the application."""

import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

config = context.config
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return url


def run_with_connection(connection):
    if connection.dialect.name != "postgresql":
        raise RuntimeError("NexusOps migrations require PostgreSQL")
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=database_url(), target_metadata=None, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    # Integration tests supply a connection inside a rolled-back transaction.
    run_with_connection(config.attributes["connection"])
else:
    engine = create_engine(database_url(), poolclass=pool.NullPool, hide_parameters=True)
    try:
        with engine.connect() as connection:
            run_with_connection(connection)
    finally:
        engine.dispose()
