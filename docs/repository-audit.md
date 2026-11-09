# Repository audit — 2026-11-09

Starting commit: `adb22b4` on `main`, with a clean working tree. No user changes
needed preservation. All tracked source, tests, SQL, dependencies, Compose, and
README were inspected. Local secrets were not printed or modified.

## Verified baseline

- All 17 existing tests pass from `backend/`; root execution fails to import `app`.
- FastAPI exposes health, general chat, customers, orders, tickets, and Data Agent chat.
- Data Agent has two predefined read-only SQL tools and a five-round tool limit.
- LangGraph 1.2.18 is both installed and declared. The committed graph always
  invokes Data Agent and has no API route or routing tests.
- No Research Agent file exists. RAG, actions, authentication, organization
  boundaries, frontend, migrations, and workflow persistence are not implemented.
- README's separate LangGraph installation and possible placeholder listing are stale.
- Docker daemon was unavailable during the initial audit. Historical live database
  and OpenAI results were not reverified; baseline tests use mocks.

## Stabilization

- Root pytest configuration supports running from root or `backend/`.
- Tests ignore local `.env`, use dummy settings, and block unmocked OpenAI/database
  requests. No live API credits are required.
- Direct dependencies are pinned to the existing environment, with Pydantic
  explicitly declared. This is not a complete transitive lockfile.
- `.env.example` contains placeholders only; existing `.env` stays ignored.
- Fixed rejection of a valid final answer after the fifth tool round; a sixth
  tool batch is still rejected. Added regression tests for both boundaries.

## Remaining risks and next milestones

- APIs are unauthenticated and queries unscoped and unbounded. Keep this application
  local and synthetic-only until milestones 2 and 3 add migrations, bounded queries,
  organization-scoped data access, authentication, and role checks.
- Compose contains a legacy local development password. Externalize it without
  rotating or resetting the existing database during deployment preparation.
- Database configuration is required at application import time; the health route
  is liveness only, not a database readiness probe.
- No public deployment, database reset, real email, or refund execution is authorized.
- Next: implement Supervisor routing, typed state, capability availability, limits,
  sanitized failures, API integration, and deterministic tests.

## Follow-up verification

The Supervisor milestone is implemented and documented in [supervisor.md](supervisor.md).
Docker Desktop was subsequently started. PostgreSQL reports healthy with one row
in each original business table and pgvector 0.8.7 enabled. The Alembic baseline
was applied with every existing row verified unchanged. Eleven integration tests
passed against temporary PostgreSQL schemas, including a real database-tool path
through the Supervisor; OpenAI remained mocked. See
[database-migrations.md](database-migrations.md) for commands and outstanding
Milestone 2 work.
