<div align="center">

# Engineering Command Center

**A RAG-powered AI assistant and engineering dashboard for software teams.**  
Ask questions about your codebase, browse GitHub repos and PRs, monitor system health, and track usage — all in one place.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.12-dc143c?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Quick Start](#quick-start) · [Features](#features) · [Architecture](#architecture) · [API Reference](#api-reference) · [Deploy](#deployment) · [Contributing](CONTRIBUTING.md)

</div>

---

## What is this?

Engineering Command Center (ECC) gives your engineering team a single pane of glass over the code they ship. It combines a **RAG-powered AI assistant** — grounded in your actual repositories via semantic search — with a **live engineering dashboard** covering GitHub activity, service health, and indexed knowledge stats.

Ask "how does our payment retry logic work?" and get a precise answer with source citations pulled directly from your codebase. No hallucinations about code that doesn't exist.

```
┌─────────────────────────────────────────────────────────────┐
│  "How does our auth middleware handle token refresh?"        │
│                                      ↓                       │
│  [Semantic search across indexed repos via Qdrant]           │
│                                      ↓                       │
│  [Gemini 2.5 Flash grounds answer in retrieved code chunks]  │
│                                      ↓                       │
│  Answer with source file citations + confidence score        │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

| | Feature | Description |
|---|---|---|
| 🤖 | **RAG AI Chat** | Ask anything about your codebase. Answers are grounded in real source code chunks retrieved from Qdrant, with source citations and a confidence score. |
| 🗂️ | **Repository Dashboard** | Browse all repos and open PRs across your GitHub organisation, with React Query-powered caching. |
| 🔍 | **Repository Scanner** | Discover, clone, and sync repos from your GitHub org. Trigger full re-indexing from the UI or CLI. |
| 🧠 | **Knowledge Base Explorer** | Inspect indexed chunk counts per repository. Run semantic searches directly against the vector store. |
| 💊 | **System Health Dashboard** | Live liveness, readiness, and full health checks for all services — Qdrant, Gemini, and GitHub. |
| 🌗 | **Dark Mode** | System-aware theme with manual toggle. CSS custom properties throughout for consistent theming. |
| 📜 | **Chat History** | Persistent session history in localStorage, grouped by Today / Yesterday / This week / Older. |
| 🔐 | **Google OAuth** | Domain-restricted login via Google OAuth 2.0. JWT-authenticated API endpoints. |

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · Poetry |
| Frontend | Next.js 15 · TypeScript · Tailwind CSS |
| Vector DB | Qdrant v1.12 (Docker) |
| LLM | Gemini 2.5 Flash |
| Embeddings | Google `text-embedding-004` (768-dim, COSINE) |
| Auth | Google OAuth 2.0 · JWT |
| Deployment | Ubuntu 22.04 · nginx · systemd · Let's Encrypt |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Your Server / VPS                      │
│                                                               │
│  ┌──────────────┐   HTTP/JSON   ┌──────────────────────────┐  │
│  │  Next.js 15  │ ◄───────────► │    FastAPI Backend        │  │
│  │  (port 3000) │               │    (port 8000)            │  │
│  └──────────────┘               └──────┬──────────┬─────────┘  │
│                                        │          │             │
│                             ┌──────────▼──┐  ┌───▼──────────┐  │
│                             │   Qdrant    │  │ External APIs │  │
│                             │ (port 6333) │  │ Gemini 2.5   │  │
│                             │  768-dim    │  │ GitHub REST  │  │
│                             │  COSINE     │  └──────────────┘  │
│                             └─────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

### RAG Pipeline

```
User question
    │
    ▼  EmbeddingService.embed_text(task_type="retrieval_query")
Query vector (768-dim)
    │
    ▼  QdrantService.search(query_vector, limit=top_k)
Top-K scored chunks
    │
    ▼  PromptBuilder.build(question, chunks)  [≤24K char context budget]
    │
    ▼  Gemini 2.5 Flash  [temperature=0.2, max_tokens=4096]
Answer + sources + confidence score
```

### Indexing Pipeline (CLI / UI trigger)

```
indexer.py --index
    │
    ▼  Discover repos (include/exclude glob filters)
    ▼  Clone / pull via HTTPS + token  [asyncio.Semaphore(4)]
    ▼  ChunkingService  →  code (sliding window) / prose (paragraph)
    ▼  EmbeddingService.embed_batch  [batches of 50, Semaphore(5)]
    ▼  QdrantService.upsert_chunks  [UUID5 IDs — idempotent re-index]
```

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12+ |
| Poetry | 1.8+ |
| Node.js | 20+ |
| Docker | 24+ |

### 1. Clone and configure

```bash
git clone https://github.com/your-org/engineering-command-center.git
cd engineering-command-center
cp .env.example .env
# Fill in GEMINI_API_KEY, GITHUB_TOKEN, and GITHUB_ORG — those three are required
```

### 2. Start Qdrant

```bash
docker compose up -d qdrant

# Verify:
curl http://localhost:6333/readyz
# → {"result":"ok"}
```

Qdrant dashboard: http://localhost:6333/dashboard

### 3. Start the backend

```bash
cd backend
poetry install
cp ../.env .env
poetry run python run.py
# API:  http://localhost:8000
# Docs: http://localhost:8000/api/v1/docs
```

```bash
# Verify:
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
cp ../.env .env.local
npm run dev
# App: http://localhost:3000
```

### 5. Index your repositories

```bash
cd backend

# Index all repos in your GitHub org:
poetry run python indexer.py --index

# Or index a single repo first (much faster for testing):
poetry run python indexer.py --index --repo payments-service

# Preview what would be indexed without embedding:
poetry run python indexer.py --dry-run

# Check collection stats:
poetry run python indexer.py --stats

# Test semantic search:
poetry run python indexer.py --search "how does payment retry work"
```

Alternatively, use the **Scanner** page at http://localhost:3000/scanner to trigger sync from the UI.

### 6. Start asking questions

Open http://localhost:3000/chat and ask anything about your indexed codebase.

---

## Configuration

All configuration is driven by environment variables. Copy `.env.example` to `.env` and fill in the values. Three variables are required for a working local setup:

| Variable | Description | How to get it |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio or GCP key with Gemini access | [aistudio.google.com](https://aistudio.google.com) |
| `GITHUB_TOKEN` | PAT with `read:org` and `repo` scopes | GitHub → Settings → Developer settings → Tokens |
| `GITHUB_ORG` | GitHub organisation slug (e.g. `acme-corp`) | Your org's URL slug |

Key optional settings:

| Variable | Default | Description |
|---|---|---|
| `REPO_INCLUDE_PATTERNS` | `["*"]` | Glob patterns — repos must match at least one |
| `REPO_EXCLUDE_PATTERNS` | `["experimental-*","poc-*"]` | Glob patterns — matching repos are skipped |
| `GITHUB_REPO_PREFIX` | _(unset)_ | Fast prefix filter applied before glob patterns |
| `REPOS_BASE_PATH` | `/Users/you/repos` | Local path where repos are cloned |
| `CHUNK_MAX_CHARS` | `4000` | Maximum characters per indexed chunk |
| `ALLOWED_EMAIL_DOMAIN` | `yourdomain.com` | Restrict Google OAuth logins to this domain |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS allowed origins |

See `.env.example` for the full list with descriptions.

---

## Project Structure

```
engineering-command-center/
├── .env.example                    # Environment variable template
├── docker-compose.yml              # Qdrant vector database
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/       # Route handlers: chat, github, health, knowledge, rag, repositories
│   │   ├── core/                   # config.py, logging.py, dependencies.py
│   │   ├── schemas/                # Pydantic request/response models
│   │   └── services/               # Business logic: gemini, github, qdrant, embedding, rag, chunker, ...
│   ├── indexer.py                  # CLI for indexing repos into Qdrant
│   ├── run.py                      # Dev server entry point
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router pages
│   │   ├── components/             # UI components: chat/, layout/, rag/, scanner/, ui/
│   │   ├── hooks/                  # React Query data hooks
│   │   ├── lib/                    # axios client, queryClient, utils, history
│   │   └── types/                  # TypeScript interfaces
│   └── package.json
└── docs/
    ├── architecture.md
    ├── developeronboarding.md
    ├── DEPLOY.md
    └── AGENT.md
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/live` | Liveness probe (always 200) |
| `GET` | `/api/v1/ready` | Readiness probe — checks Qdrant |
| `GET` | `/api/v1/health` | Full health check — Qdrant + Gemini + GitHub |
| `POST` | `/api/v1/chat` | Direct multi-turn Gemini chat |
| `POST` | `/api/v1/rag/chat` | RAG chat grounded in indexed codebase |
| `GET` | `/api/v1/github/repos` | List org repositories |
| `GET` | `/api/v1/github/repos/{repo}/pulls` | List open PRs for a repository |
| `POST` | `/api/v1/repositories/sync` | Trigger repository sync |
| `GET` | `/api/v1/repositories` | List synced repositories |
| `GET` | `/api/v1/knowledge/stats` | Qdrant collection statistics |
| `GET` | `/api/v1/knowledge/search` | Semantic search over indexed chunks |
| `GET` | `/api/v1/knowledge/repos/{name}` | Chunks for a specific repository |

Full interactive docs: **http://localhost:8000/api/v1/docs**

---

## Running Tests

```bash
cd backend

# Run all tests:
poetry run pytest -v

# With coverage report:
poetry run pytest --cov=app --cov-report=term-missing
```

### Code Quality

**Backend:**
```bash
poetry run ruff format .     # format
poetry run ruff check .      # lint
poetry run mypy app/         # type check
```

**Frontend:**
```bash
npm run lint                 # ESLint
npm run type-check           # tsc --noEmit
```

---

## Deployment

The production stack runs on a single Ubuntu 22.04 VPS (tested on AWS Lightsail). The architecture is:

```
Internet → nginx (80/443) → Next.js (127.0.0.1:3000)
                          → FastAPI (127.0.0.1:8000) → Qdrant (Docker, localhost-only)
```

See **[DEPLOY.md](DEPLOY.md)** for the complete step-by-step production deployment guide covering:

- System setup (Docker, Python 3.11, Node.js 20)
- Google OAuth credentials
- systemd services for backend and frontend
- nginx reverse proxy configuration
- Let's Encrypt SSL with auto-renewal
- UFW firewall hardening
- Security headers and TLS 1.3

---

## Roadmap

- [ ] Streaming responses for RAG chat (Server-Sent Events)
- [ ] Per-repository access control (allowlist by team)
- [ ] Slack bot integration for chat queries
- [ ] Webhook-triggered incremental re-indexing on push
- [ ] Multi-LLM support (Claude, GPT-4o) via provider abstraction
- [ ] Admin panel for usage metrics and user management
- [ ] Helm chart for Kubernetes deployment
- [ ] OpenTelemetry tracing

---

## Contributing

Contributions are very welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

For bugs and feature requests, open a [GitHub issue](https://github.com/your-org/engineering-command-center/issues).

---

## License

[MIT](LICENSE) — Keshav Upadhyaya and contributors.

---

<div align="center">

If this project is useful to your team, consider giving it a star. ⭐

</div>
