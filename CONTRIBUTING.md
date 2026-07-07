# Contributing to Engineering Command Center

Thank you for your interest in contributing. This document covers everything you need to get from zero to a merged pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Requesting Features](#requesting-features)
  - [Submitting Pull Requests](#submitting-pull-requests)
- [Development Setup](#development-setup)
- [Project Conventions](#project-conventions)
  - [Commit Messages](#commit-messages)
  - [Backend Conventions](#backend-conventions)
  - [Frontend Conventions](#frontend-conventions)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Adding a New Feature — Checklist](#adding-a-new-feature--checklist)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to abide by its terms.

---

## How to Contribute

### Reporting Bugs

Before opening a bug report, search [existing issues](https://github.com/your-org/engineering-command-center/issues) to avoid duplicates.

When filing a bug, include:

- A clear, descriptive title.
- Steps to reproduce the problem.
- What you expected to happen.
- What actually happened (paste error output or logs).
- Your environment: OS, Python version, Node.js version, Docker version.

### Requesting Features

Open a [GitHub issue](https://github.com/your-org/engineering-command-center/issues/new) with the label `enhancement`. Describe:

- The problem you are trying to solve.
- Your proposed solution or API surface.
- Any alternatives you considered.

### Submitting Pull Requests

1. **Fork** the repository and create your branch from `main`.
2. **Follow the development setup** below to get a working local environment.
3. **Make your changes**, keeping each PR focused on a single concern.
4. **Write or update tests** for any changed behaviour (coverage target: 80%).
5. **Run the full quality suite** (lint, format, type-check, tests) before pushing.
6. **Open a pull request** against `main` with a clear description of what changed and why.

Pull requests are reviewed within a few days. Smaller, well-scoped PRs are reviewed faster.

---

## Development Setup

Full setup instructions are in [docs/developeronboarding.md](docs/developeronboarding.md). The short version:

```bash
# 1. Clone and configure
git clone https://github.com/your-org/engineering-command-center.git
cd engineering-command-center
cp .env.example .env
# Fill in GEMINI_API_KEY, GITHUB_TOKEN, GITHUB_ORG

# 2. Start Qdrant
docker compose up -d qdrant

# 3. Start the backend
cd backend
poetry install
cp ../.env .env
poetry run python run.py

# 4. Start the frontend (new terminal)
cd frontend
npm install
cp ../.env .env.local
npm run dev
```

---

## Project Conventions

### Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must follow this format:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | A new feature visible to users or operators |
| `fix` | A bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | A code change that improves performance |
| `test` | Adding or correcting tests |
| `docs` | Documentation only changes |
| `chore` | Build process, dependency updates, tooling |
| `ci` | CI configuration changes |

**Scopes** (optional but encouraged): `backend`, `frontend`, `rag`, `indexer`, `docker`, `deps`.

**Examples:**

```
feat(rag): add per-repository filter to RAG chat endpoint
fix(frontend): correct dark mode flash on initial page load
test(backend): add unit tests for ChunkingService prose strategy
docs: add Helm chart deployment section to DEPLOY.md
chore(deps): bump qdrant-client to 1.13.0
```

Breaking changes must include `BREAKING CHANGE:` in the footer:

```
feat(api): rename /knowledge/search to /knowledge/query

BREAKING CHANGE: clients must update the endpoint URL.
```

### Backend Conventions

- **Language**: Python 3.12. Use `datetime.UTC`, `StrEnum`, and other modern stdlib features.
- **Formatter/Linter**: `ruff`. Configuration in `pyproject.toml`. Run `poetry run ruff format . && poetry run ruff check .` before committing.
- **Type checker**: `mypy` with strict mode. All public functions must have type annotations.
- **Architecture**: Strict layer separation — routes → schemas → services → external clients. Services must never import from `api/`. See [docs/architecture.md](docs/architecture.md).
- **Dependency injection**: Wire all services via `app/core/dependencies.py` using FastAPI's `Depends()`.
- **New routes**: Must be registered in `backend/app/api/v1/router.py`.
- **Schemas**: Define Pydantic request/response models in `backend/app/schemas/`. Any schema change requires a corresponding update to the TypeScript types in `frontend/src/types/`.
- **Error handling**: Raise `HTTPException` in route handlers. Services raise domain-specific exceptions; routes translate them.
- **Logging**: Use `structlog` throughout. Never use `print()`.
- **Retries**: Wrap all Gemini and GitHub calls with `tenacity` (3 retries, exponential backoff + jitter).
- **Qdrant point IDs**: UUID5 based on `repo:file_path:chunk_index`. Do not change this scheme — it ensures idempotent re-indexing.

### Frontend Conventions

- **Language**: TypeScript with strict mode. No `any` unless absolutely unavoidable.
- **Linter/Formatter**: ESLint (`npm run lint`) and Prettier (via ESLint config).
- **Component rules**:
  - Pages in `src/app/<route>/page.tsx` are server components by default.
  - Components that use hooks, browser APIs, or event handlers must have `"use client"` at the top.
  - The `/chat` route is full-screen (no sidebar). Add any new full-screen routes to `FULL_SCREEN_ROUTES` in `AppShell`.
- **Data fetching**: Use React Query hooks from `src/hooks/`. Do not fetch directly in components.
- **Theming**: All colours use CSS custom properties (`--bg-primary`, `--text-primary`, etc.) defined in `globals.css`. Never use Tailwind `dark:` variants.
- **TypeScript types**: Mirror backend Pydantic schemas exactly. Keep `src/types/` in sync with `backend/app/schemas/`.

---

## Testing

### Backend

Tests live in `backend/tests/`. Use `pytest` with `httpx.AsyncClient` for integration tests.

```bash
cd backend
poetry run pytest -v
poetry run pytest --cov=app --cov-report=term-missing
```

Guidelines:

- **Unit test** all service-layer logic.
- **Integration test** route handlers using `httpx.AsyncClient(app=app)`.
- **Mock all external services** — Gemini, GitHub, and Qdrant. Tests must never hit real APIs.
- `EmbeddingService` tests must mock `google.generativeai`. The rate-limiting semaphore is lazy-initialised, so async test context is fine.
- Minimum coverage target: **80%**.

### Frontend

```bash
cd frontend
npm run type-check    # tsc --noEmit — catches type errors without building
npm run lint          # ESLint
```

---

## Code Quality

Run the full quality suite before opening a PR:

```bash
# Backend
cd backend
poetry run ruff format .
poetry run ruff check .
poetry run mypy app/
poetry run pytest --cov=app

# Frontend
cd frontend
npm run lint
npm run type-check
```

All of these must pass cleanly. PRs with lint errors or type errors will not be merged.

---

## Adding a New Feature — Checklist

Use this checklist when building a new end-to-end feature:

- [ ] Define Pydantic schema in `backend/app/schemas/`
- [ ] Implement service logic in `backend/app/services/`
- [ ] Add route handler in `backend/app/api/v1/endpoints/`
- [ ] Register route in `backend/app/api/v1/router.py`
- [ ] Add TypeScript types in `frontend/src/types/` (mirroring the schema)
- [ ] Create React Query hook in `frontend/src/hooks/`
- [ ] Build page in `frontend/src/app/<feature>/page.tsx`
- [ ] Add sidebar entry in `frontend/src/components/layout/Sidebar.tsx`
- [ ] Write tests in `backend/tests/`
- [ ] Update `README.md` if the feature changes user-facing behaviour
- [ ] Update `.env.example` if the feature introduces new environment variables

---

Thank you for contributing.
