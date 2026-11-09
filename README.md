# NexusOps AI

### Enterprise AI Operations & Multi-Agent Automation Platform

NexusOps AI is an AI-powered enterprise operations platform designed to help businesses retrieve operational data, investigate customer issues, and automate multi-step workflows using natural language.

Built with **Python, FastAPI, OpenAI, LangGraph, PostgreSQL, pgvector, and Docker**, the project demonstrates how large language models can interact with real databases, execute predefined tools, and coordinate business workflows.

The platform is under active development, with the long-term goal of supporting multiple specialized AI agents, document retrieval, human-approved actions, and an interactive web dashboard.

## Key Features

### Implemented

- **AI-powered business assistant:** Ask operational questions in natural language.
- **PostgreSQL integration:** Store and retrieve customer, order, and support ticket records.
- **OpenAI function calling:** Allow the AI to select and execute predefined database tools.
- **Data Agent:** Retrieve delayed orders and open support tickets.
- **Multi-tool execution:** Combine information from multiple database tools in one response.
- **Multi-step tool calling:** Support multiple rounds of AI tool requests, with a maximum of five tool-execution rounds.
- **REST APIs:** Access business records and AI functionality through FastAPI.
- **LangGraph workflow:** Execute the existing Data Agent through a graph-based workflow.
- **Dockerized database:** Run PostgreSQL with pgvector locally.
- **Automated testing:** Tests covering API behavior, database tool logic, and agent execution.

### Planned

- Intelligent Supervisor Agent for routing requests between specialized agents
- Research Agent with retrieval-augmented generation (RAG)
- Document ingestion, embeddings, semantic search, and citations
- Action Agent for drafting business communications and proposing operational changes
- Human-in-the-loop approvals
- MCP-based integrations
- Next.js dashboard with agent activity and workflow history
- Authentication, role-based access control, and organization-level data isolation
- Agent evaluation, observability, and deployment

## Example Use Cases

**1. Delayed Order Investigation**

User:

> Which orders are delayed?

NexusOps AI retrieves matching orders from PostgreSQL and generates a natural-language response.

Example:

> The delayed order is for Wireless Headphones, placed by Alex Johnson.

**2. Customer Support Analysis**

User:

> Which customers have open support tickets?

The Data Agent retrieves open tickets and identifies affected customers.

**3. Cross-System Business Questions**

User:

> Which customers have delayed orders and open support tickets?

NexusOps AI can execute both database tools and combine their results into one answer.

**4. Planned: Automated Customer Support Workflow**

User:

> Find customers with delayed orders, review our refund policy, and prepare apology emails.

The planned Supervisor will coordinate the Data, Research, and Action agents. Customer communications will require approval before sending.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| AI | OpenAI API, function calling |
| Agent orchestration | LangGraph |
| Database | PostgreSQL 17 |
| Vector database | pgvector (enabled; retrieval features planned) |
| Database access | SQLAlchemy, Psycopg |
| Infrastructure | Docker, Docker Compose |
| Testing | Pytest, FastAPI TestClient, unittest.mock |
| Planned frontend | Next.js, React, TypeScript |

## Architecture

Current workflow:

```text
User
  |
  v
FastAPI / Python
  |
  v
OpenAI
  |
  v
Tool Selection
  |
  +---- get_delayed_orders()
  |
  +---- get_open_support_tickets()
  |
  v
PostgreSQL
  |
  v
OpenAI generates response
  |
  v
User receives answer
```

A basic LangGraph workflow is also available:

```text
START
  |
  v
Data Agent
  |
  v
END
```

The current LangGraph workflow does not yet perform intelligent routing between multiple agents.

### Target Architecture

```text
Next.js Dashboard
       |
       v
FastAPI Backend
       |
       v
LangGraph Supervisor
       |
       +---- Data Agent
       |       |
       |       v
       |   PostgreSQL
       |
       +---- Research Agent
       |       |
       |       v
       |   Documents + RAG + pgvector
       |
       +---- Action Agent
               |
               v
         Human Approval
               |
               v
         Authorized Actions
```

## Project Structure

The following shows the main implemented components, rather than every file in the repository.

```text
nexusops-ai/
|
|-- backend/
|   |
|   |-- app/
|   |   |-- agents/
|   |   |   |-- data_agent.py
|   |   |   |-- data_agent_service.py
|   |   |   |-- supervisor.py
|   |   |   `-- research_agent.py (placeholder, if created)
|   |   |
|   |   |-- services/
|   |   |   `-- openai_service.py
|   |   |
|   |   |-- database.py
|   |   `-- main.py
|   |
|   |-- database/
|   |   |-- schema.sql
|   |   `-- seed.sql
|   |
|   |-- tests/
|   |   |-- test_health.py
|   |   |-- test_ai.py
|   |   |-- test_database.py
|   |   |-- test_data_agent.py
|   |   |-- test_data_tools.py
|   |   `-- test_data_agent_service.py
|   |
|   |-- requirements.txt
|   `-- .env (local only; not committed)
|
|-- docker-compose.yml
`-- README.md
```

## Getting Started

### Prerequisites

- Python 3.12
- Docker Desktop
- Git
- An OpenAI API key

### 1. Clone the repository

```bash
git clone https://github.com/karthik-35/nexusops-ai.git
cd nexusops-ai
```

### 2. Set up Python

```bash
cd backend

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

LangGraph is included. Direct dependencies are pinned to the verified development environment.

### 3. Configure environment variables

If `backend/.env` already exists, preserve it. Otherwise copy `backend/.env.example` and replace its placeholders:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini

DATABASE_URL=postgresql+psycopg://nexusops:replace-with-local-database-password@127.0.0.1:5433/nexusops
```

Use the password for your existing local database. The example does not contain usable credentials.

**Never commit `.env` or real API keys to GitHub.**

### 4. Start PostgreSQL

Open Docker Desktop, then run from the project root:

```bash
cd ..
docker compose up -d
docker compose ps
```

The PostgreSQL container should report a healthy status.

The database is accessible locally on port `5433`.

### 5. Initialize the database

For a **fresh database only**, run (preserve an existing database):

```bash
docker compose exec -T postgres \
  psql -U nexusops -d nexusops \
  < backend/database/schema.sql
```

Load the sample data:

```bash
docker compose exec -T postgres \
  psql -U nexusops -d nexusops \
  < backend/database/seed.sql
```

The sample data includes fictional customers, orders, and support tickets.

### 6. Run FastAPI

```bash
cd backend
source .venv/bin/activate

uvicorn app.main:app --reload
```

Open:

http://127.0.0.1:8000/docs

If port `8000` is occupied, use:

```bash
uvicorn app.main:app --reload --port 8001
```

Then open http://127.0.0.1:8001/docs.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Backend health check |
| POST | `/api/v1/ai/chat` | General OpenAI chat |
| GET | `/api/v1/customers` | Retrieve customers |
| GET | `/api/v1/orders` | Retrieve orders |
| GET | `/api/v1/tickets` | Retrieve support tickets |
| POST | `/api/v1/agents/data/chat` | Ask the Data Agent a question |

### Example Data Agent Request

```http
POST /api/v1/agents/data/chat
Content-Type: application/json
```

```json
{
  "message": "Which customers have delayed orders and open support tickets?"
}
```

Example response:

```json
{
  "answer": "Alex Johnson has both delayed orders and open support tickets."
}
```

## Testing

Run from the repository root:

```bash
backend/.venv/bin/python -m pytest -q
```

Or run from `backend/`:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

Latest verified result during development:

```text
19 passed
```

Tests cover:

- Health endpoint behavior
- OpenAI endpoint responses and errors
- Database API responses
- Data Agent API validation and error handling
- Database tool output processing
- Multiple tool calls
- Multi-round agent execution

The unit suite uses mocks and blocks unmocked OpenAI and database access. It ignores local `.env` credentials. Successful unit tests do not replace integration, security, or production testing.

## Testing the Data Agent Manually

With PostgreSQL running and the environment configured:

```bash
cd backend
source .venv/bin/activate
```

Ask about delayed orders:

```bash
python -c "from app.agents.data_agent_service import ask_data_agent; print(ask_data_agent('Which orders are delayed?'))"
```

Ask about open tickets:

```bash
python -c "from app.agents.data_agent_service import ask_data_agent; print(ask_data_agent('Which customers have open support tickets?'))"
```

Ask a combined question:

```bash
python -c "from app.agents.data_agent_service import ask_data_agent; print(ask_data_agent('Which customers have delayed orders and open support tickets?'))"
```

## Security Considerations

NexusOps AI currently uses predefined, read-only SQL tools for AI-driven database retrieval. The AI does not execute arbitrary SQL statements.

The current implementation is intended for local development and demonstrations.

Before public deployment, the platform needs authentication, authorization, tenant isolation, rate limiting, secret management, audit logging, and stronger error handling.

Do not expose the existing database APIs publicly or use real customer data until appropriate security controls are implemented.

See [the repository audit](docs/repository-audit.md) for verified baseline findings and remaining risks.

## Development Roadmap

- [x] FastAPI backend
- [x] PostgreSQL integration
- [x] Docker database setup
- [x] OpenAI chat integration
- [x] Read-only database tools
- [x] Multi-tool Data Agent
- [x] Multi-round tool execution
- [x] Automated tests
- [x] Basic LangGraph workflow
- [ ] Intelligent Supervisor routing
- [ ] Research Agent with RAG
- [ ] pgvector semantic document search
- [ ] Action Agent
- [ ] Human approval workflows
- [ ] Next.js frontend
- [ ] Authentication and authorization
- [ ] Monitoring and agent evaluations
- [ ] Deployment

## Project Goals

NexusOps AI is being developed as a practical exploration of:

- Agentic AI and multi-agent systems
- LLM function calling and orchestration
- Enterprise backend engineering
- Relational and vector databases
- Retrieval-augmented generation
- Secure AI-assisted automation
- Full-stack application development
- Testing and production-oriented software design

The long-term objective is to demonstrate an end-to-end enterprise workflow where specialized AI agents retrieve information, consult documents, propose actions, and coordinate through a controlled approval process.

## License

No license has been specified yet. All rights remain reserved unless a license is added.

---

**NexusOps AI — From natural-language questions to intelligent business workflows.**
