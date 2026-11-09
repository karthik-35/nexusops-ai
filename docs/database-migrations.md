# Database migrations

Alembic records which schema revisions have been applied to PostgreSQL. Future
schema changes should be reviewed revisions, not edits to a live database through
the old bootstrap SQL. [Alembic's tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
describes the underlying migration workflow.

## Current status

Migration `0001_business_schema` is a tested baseline for the existing `customers`,
`orders`, and `support_tickets` tables. It supports both fresh databases and the
previous `database/schema.sql` setup. It is the foundation of Milestone 2, not the
completed business data layer.

On 2026-11-09, the existing local database was adopted successfully. Every row
was compared before and after adoption inside the same transaction: one customer,
one order, and one support ticket, all unchanged. pgvector 0.8.7 was verified as
enabled. No database was dropped, reset, or reseeded.

## Apply migrations

From the repository root, using the existing `backend/.env`:

```bash
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
```

Or from `backend/` with its virtual environment active:

```bash
python -m alembic upgrade head
```

Credentials come from `DATABASE_URL`, never from `alembic.ini`. Use the configured
PostgreSQL instance on local port 5433. These migrations do not require OpenAI.

For a fresh database, the baseline creates tables. For existing tables it validates
columns, types, nullability, ID generation, defaults, primary keys, required unique
constraints, customer foreign keys, and the nonnegative order amount constraint.
It validates all existing tables before creating missing ones. An incompatible
schema causes failure instead of silent adoption. Do not bypass that failure with
`alembic stamp head`; inspect the difference and write a reviewed migration.

The baseline does not add or remove business records, change existing tables, or
install/remove pgvector. The optional original synthetic seed remains available
for a fresh database. Schema upgrades are transactional in PostgreSQL. Baseline
downgrade is intentionally disabled because dropping adopted tables could destroy
existing records; use a reviewed forward migration.

Offline SQL generation (`upgrade head --sql`) is supported **for a fresh database
only**. Existing-database adoption requires an online schema inspection.

## Tests

Routine tests include a create-only offline SQL check:

```bash
backend/.venv/bin/python -m pytest -q
```

Run the separate PostgreSQL suite explicitly with Docker running:

```bash
NEXUSOPS_RUN_DB_TESTS=1 backend/.venv/bin/python -m pytest backend/integration_tests -q --tb=short
```

Each test creates a unique schema inside a transaction, sets its local search path
to that schema, and rolls back everything at the end. The suite verifies fresh
setup, existing-row and sequence preservation, repeated upgrades, partial schema
adoption, drift rejection, constraints, cross-schema foreign keys, downgrade
protection, and real database APIs/tools through the Supervisor. OpenAI remains
mocked. Run this suite separately from unit tests, which intentionally replace
database settings with dummy values and block external services.

Eleven PostgreSQL integration tests passed; zero temporary schemas remained after
the run. The main database's business rows remained unchanged.

## Next data-layer work

1. Add organizations and organization-scoped relationships through a new revision,
   assigning existing synthetic records to NovaMart without changing their IDs.
2. Introduce a trusted request identity and enforce organization filters in every
   API and tool. Implement authentication/roles before serving multiple organizations;
   an arbitrary client-supplied organization header is not authorization.
3. Add bounded pagination/filtering and exact aggregate tools. Limited row retrieval
   must never masquerade as a complete count.
4. Add richer, repeatable synthetic fixtures and cross-organization integration tests.

Until those steps are implemented, the APIs remain local, unauthenticated, and
single-dataset demonstrations. This migration does not establish tenant isolation.
