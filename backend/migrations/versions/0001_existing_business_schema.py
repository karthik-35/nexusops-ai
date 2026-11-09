"""Create or safely adopt the original NovaMart business tables.

This revision is intentionally self-contained. Future application models must
not change what an already-published migration creates or validates.
"""

import re

from alembic import context, op
import sqlalchemy as sa

revision = "0001_business_schema"
down_revision = None
branch_labels = None
depends_on = None


def baseline_tables() -> sa.MetaData:
    metadata = sa.MetaData()
    sa.Table(
        "customers", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
    )
    sa.Table(
        "orders", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("product", sa.String(150), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.CheckConstraint("amount >= 0"),
    )
    sa.Table(
        "support_tickets", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
    )
    return metadata


def _normalized(expression: str) -> str:
    return re.sub(r"[\s()]|::(?:numeric|text|character varying)", "", expression)


def validate_existing_table(inspector, table: sa.Table) -> None:
    """Fail closed on schema drift; do not stamp an incompatible database."""
    actual = {column["name"]: column for column in inspector.get_columns(table.name)}

    def incompatible():
        raise RuntimeError(
            f"Existing table '{table.name}' differs from the baseline. "
            "No adoption was performed; review the schema before migrating."
        )

    if set(actual) != set(table.columns.keys()):
        incompatible()
    for column in table.columns:
        found = actual[column.name]
        if (
            str(found["type"]) != str(column.type)
            or found["nullable"] != column.nullable
        ):
            incompatible()
        if column.primary_key:
            # Existing SERIAL or IDENTITY IDs must continue generating values.
            if not (found.get("identity") or "nextval(" in (found.get("default") or "")):
                incompatible()
        elif column.server_default is not None:
            if _normalized(found.get("default") or "") != repr(column.server_default.arg):
                incompatible()
        elif found.get("default") is not None:
            incompatible()

    if inspector.get_pk_constraint(table.name)["constrained_columns"] != ["id"]:
        incompatible()
    if table.name == "customers":
        unique_columns = [set(c["column_names"]) for c in inspector.get_unique_constraints(table.name)]
        if {"email"} not in unique_columns:
            incompatible()
    else:
        foreign_keys = inspector.get_foreign_keys(table.name)
        current_schema = inspector.bind.scalar(sa.text("SELECT current_schema()"))
        if not any(
            fk["constrained_columns"] == ["customer_id"]
            and fk["referred_table"] == "customers"
            and fk["referred_columns"] == ["id"]
            and fk.get("referred_schema") in (None, current_schema)
            and fk.get("options", {}).get("ondelete") in (None, "NO ACTION")
            for fk in foreign_keys
        ):
            incompatible()
    if table.name == "orders":
        checks = inspector.get_check_constraints(table.name)
        if not any(_normalized(c["sqltext"]) == "amount>=0" for c in checks):
            incompatible()


def upgrade() -> None:
    metadata = baseline_tables()
    if context.is_offline_mode():
        # Offline SQL is for a fresh database only: adoption needs inspection.
        metadata.create_all(op.get_bind(), checkfirst=False)
        return

    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing = set(inspector.get_table_names())
    # Validate all existing tables before creating any missing ones.
    for table in metadata.sorted_tables:
        if table.name in existing:
            validate_existing_table(inspector, table)
    for table in metadata.sorted_tables:
        if table.name not in existing:
            table.create(connection, checkfirst=False)


def downgrade() -> None:
    raise RuntimeError(
        "Baseline downgrade is disabled to preserve business data. "
        "Use a reviewed forward migration instead."
    )
