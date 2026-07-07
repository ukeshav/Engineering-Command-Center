# AI Engineering Command Center

A unified engineering intelligence platform giving your team a single pane of glass over repositories, pull requests, system health, and a RAG-powered AI assistant grounded in your actual codebase.

## Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.12 + FastAPI + Poetry      |
| Frontend   | Next.js 15 + TypeScript + Tailwind  |
| Vector DB  | Qdrant (Docker)                     |
| LLM        | Gemini 2.5 Flash                    |
| Embeddings | Google text-embedding-004 (768-dim) |
| Deployment | AWS Lightsail                       |

## Features

- **AI Chat** — Ask questions about your codebase, get answers grounded in actual source code via RAG
- **Repository Scanner** — Discover, clone, and sync repos from a GitHub org
- **Knowledge Base** — Index repositories into Qdrant for semantic search
- **System Health** — Live/Ready/Full health checks for all services
- **Repository Dashboard** — Browse org repos and open PRs
- **Dark Mode** — System-aware theme with manual toggle
- **Chat History** — Persistent session history in localStorage

## Quick Start

### Prerequisites

| Tool          | Version | Install                            |
|---------------|---------|------------------------------------|
| Python        | 3.12+   | `pyenv install 3.12`               |
| Poetry        | 1.8+    | `pip install poetry`               |
| Node.js       | 20+     | `nvm install 20`                   |
| Docker        | 24+     | docker.com/get-docker              |

### 1. Clone & configure

```bash
git clone git@github.com:your-org/engineering-command-center.git
cd engineering-command-center
cp .env.example .env
# Edit .env — GEMINI_API_KEY, GITHUB_TOKEN, and GITHUB_ORG are required
```

### 2. Start Qdrant

```bash
docker compose up -d qdrant

# Verify it's healthy:
curl http://localhost:6333/readyz
# → {"result":"ok"}
```

### 3. Start the backend

```bash
cd backend
poetry install
cp ../.env .env          # backend reads .env from its own directory
poetry run python run.py
# API: http://localhost:8000
# Docs: http://localhost:8000/api/v1/docs
```

Verify:
```bash
curl http://localhost:8000/api/v1/live
# → {"status":"alive"}
curl http://localhost:8000/api/v1/ready
# → {"status":"ready","checks":{"qdrant":"ok"}}
```

### 4. Start the frontend

```bash
# New terminal tab
cd frontend
npm install
cp ../.env .env.local    # Next.js reads NEXT_PUBLIC_* from .env.local
npm run dev
# App: http://localhost:3000
```

### 5. Sync and index repositories

```bash
# From the backend directory (with .env present)
cd backend

# Discover and clone all repos in the org, then index them:
poetry run python indexer.py --index

# Or index a single repo:
poetry run python indexer.py --index --repo payments-service

# Check what would be indexed without embedding:
poetry run python indexer.py --dry-run

# View collection stats:
poetry run python indexer.py --stats

# Test semantic search:
poetry run python indexer.py --search "how does payment retry work"
```

Alternatively, use the **Scanner** page in the frontend UI to trigger sync via the API.

### 6. Ask the AI assistant

Open http://localhost:3000/chat and ask anything about your indexed codebase.

## Project Structure

```
engineering-command-center/
├── .env.example                  # Environment variable template
├── docker-compose.yml            # Qdrant service
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Route handlers (chat, github, health, knowledge, rag, repositories)
│   │   ├── core/                 # config.py, logging.py, dependencies.py
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── services/             # Business logic (gemini, github, qdrant, embedding, rag, chunker, ...)
│   │   └── main.py
│   ├── indexer.py                # CLI for indexing repos into Qdrant
│   ├── run.py                    # Dev server entry point
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   ├── components/           # UI components (chat/, layout/, rag/, scanner/, ui/)
│   │   ├── hooks/                # React Query data hooks
│   │   ├── lib/                  # axios client, queryClient, utils, history
│   │   └── types/                # TypeScript interfaces
│   └── package.json
└── docs/
    ├── architecture.md
    ├── developeronboarding.md
    └── AGENT.md
```

## API Reference

| Method | Path                               | Description                      |
|--------|------------------------------------|----------------------------------|
| GET    | /api/v1/live                       | Liveness probe                   |
| GET    | /api/v1/ready                      | Readiness probe (checks Qdrant)  |
| GET    | /api/v1/health                     | Full health check                |
| POST   | /api/v1/chat                       | Direct Gemini chat               |
| POST   | /api/v1/rag/chat                   | RAG chat (grounded in codebase)  |
| GET    | /api/v1/github/repos               | List org repositories            |
| GET    | /api/v1/github/repos/{r}/pulls     | List open PRs                    |
| POST   | /api/v1/repositories/sync          | Trigger repo sync                |
| GET    | /api/v1/repositories               | List synced repositories         |
| GET    | /api/v1/knowledge/stats            | Qdrant collection stats          |
| GET    | /api/v1/knowledge/search           | Semantic search                  |
| GET    | /api/v1/knowledge/repos/{name}     | Chunks for a specific repo       |

Full interactive docs at http://localhost:8000/api/v1/docs.

## Running Tests

```bash
cd backend
poetry run pytest -v
poetry run pytest --cov=app --cov-report=term-missing
```

## Environment Variables

See `.env.example` for all variables and descriptions. The three required variables for a working local setup are:

| Variable         | Description                                      |
|-----------------|--------------------------------------------------|
| `GEMINI_API_KEY` | Google AI Studio or GCP key with Gemini access  |
| `GITHUB_TOKEN`   | PAT with `read:org` and `repo` scopes           |
| `GITHUB_ORG`     | GitHub organisation slug (e.g. `your-org`) |
