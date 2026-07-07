# Developer Onboarding — Engineering Command Center

Welcome. This document gets you from zero to a fully running local environment including the AI chat.

## Prerequisites

| Tool       | Version | Install                                |
|------------|---------|----------------------------------------|
| Python     | 3.12+   | `pyenv install 3.12` or python.org     |
| Poetry     | 1.8+    | `pip install poetry`                   |
| Node.js    | 20+     | `nvm install 20` or nodejs.org         |
| Docker     | 24+     | docker.com/get-docker                  |
| Git        | any     | `brew install git`                     |

## Step 1 — Get the code

```bash
git clone git@github.com:your-org/engineering-command-center.git
cd engineering-command-center
```

## Step 2 — Configure environment

```bash
cp .env.example .env
```

The `.env` file has sensible defaults for local development. The three variables you must fill in:

| Variable         | How to get it                                                                    |
|-----------------|----------------------------------------------------------------------------------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API key                  |
| `GITHUB_TOKEN`   | github.com → Settings → Developer settings → Personal access tokens → Classic. Needs `read:org` and `repo` scopes. |
| `GITHUB_ORG`     | Your GitHub organisation slug, e.g. `your-org`                                  |

Everything else can stay as the default for local development.

## Step 3 — Start Qdrant (vector database)

```bash
docker compose up -d qdrant

# Wait ~3 seconds, then verify:
curl http://localhost:6333/readyz
# Expected: {"result":"ok"}
```

Qdrant's web UI is available at http://localhost:6333/dashboard.

## Step 4 — Start the backend

```bash
cd backend
poetry install               # installs all Python dependencies
cp ../.env .env              # backend reads .env from its own directory
poetry run python run.py
```

You should see structured log output and:
```
Uvicorn running on http://0.0.0.0:8000
```

Verify with:
```bash
curl http://localhost:8000/api/v1/live
# → {"status":"alive"}

curl http://localhost:8000/api/v1/ready
# → {"status":"ready","checks":{"qdrant":"ok"}}
```

Interactive API docs: http://localhost:8000/api/v1/docs

## Step 5 — Start the frontend

Open a **new terminal tab**:

```bash
cd frontend
npm install
cp ../.env .env.local        # Next.js reads NEXT_PUBLIC_* vars from .env.local
npm run dev
```

App loads at http://localhost:3000.

## Step 6 — Sync and index your repositories

This is what makes the AI assistant useful. It clones your org's repos and embeds them into Qdrant.

```bash
# From the backend directory:
cd backend

# Sync all repos in your GitHub org and index them:
poetry run python indexer.py --index

# Or target a single repo first (much faster for testing):
poetry run python indexer.py --index --repo <repo-name>

# Preview what would be indexed without actually embedding:
poetry run python indexer.py --dry-run

# Check indexed stats:
poetry run python indexer.py --stats

# Test that search is working:
poetry run python indexer.py --search "authentication flow"
```

Indexing time depends on the number and size of repos. Expect ~2–5 minutes for a typical microservice (~50k lines of code).

You can also trigger sync via the **Scanner** page in the UI (http://localhost:3000/scanner).

## Step 7 — Verify the full stack

1. **Health** (http://localhost:3000/health) — All three checks should show green.
2. **Repositories** (http://localhost:3000/repositories) — Your org's repos should load.
3. **Scanner** (http://localhost:3000/scanner) — Shows sync status per repo.
4. **Knowledge** (http://localhost:3000/knowledge) — Shows indexed chunk counts per repo.
5. **AI Chat** (http://localhost:3000/chat) — Ask "How does authentication work?" — you should get an answer with source citations.

## Running Tests

```bash
cd backend
poetry run pytest -v
poetry run pytest --cov=app --cov-report=term-missing
```

## Code Quality

**Backend (Python):**
```bash
poetry run ruff check .          # lint
poetry run ruff format .         # format
poetry run mypy app/             # type check
```

**Frontend (TypeScript):**
```bash
npm run lint                     # ESLint
npm run type-check               # tsc --noEmit
```

## Project Structure

```
backend/app/
├── api/v1/endpoints/   chat.py | github.py | health.py | knowledge.py | rag.py | repositories.py
├── core/               config.py | logging.py | dependencies.py
├── schemas/            chat.py | github.py | health.py | knowledge.py | rag.py | repository_scan.py
├── services/           chunker.py | embedding.py | gemini.py | github.py | prompt_builder.py
│                       qdrant.py | rag.py | repository_scanner.py | retriever.py
├── main.py
└── indexer.py          (CLI: --index | --dry-run | --stats | --search | --delete-repo)

frontend/src/
├── app/                chat/ | health/ | knowledge/ | repositories/ | rag/ | scanner/
├── components/         chat/ | layout/ | rag/ | scanner/ | ui/
├── hooks/              useChatHistory.ts | useHealth.ts | useRag.ts | useRepositories.ts | useScanner.ts
├── lib/                api.ts | history.ts | queryClient.ts | utils.ts
└── types/              chat.ts | index.ts | rag.ts | scanner.ts
```

## Adding a New Feature — Checklist

- [ ] Define Pydantic schema in `backend/app/schemas/`
- [ ] Implement service logic in `backend/app/services/`
- [ ] Create route handler in `backend/app/api/v1/endpoints/`
- [ ] Register route in `backend/app/api/v1/router.py`
- [ ] Add TypeScript types in `frontend/src/types/`
- [ ] Create React Query hook in `frontend/src/hooks/`
- [ ] Build page in `frontend/src/app/<feature>/page.tsx`
- [ ] Add sidebar link in `frontend/src/components/layout/Sidebar.tsx`
- [ ] Write tests in `backend/tests/`

## Common Issues

**Backend won't start — `ValidationError` on settings**  
→ A required env var is missing or mistyped. The error message names the field. Check `.env` exists in `backend/`.

**Qdrant connection refused**  
→ Run `docker compose up -d qdrant` and wait ~5 seconds. Check `docker ps` to confirm it's running.

**GitHub API 401 Unauthorized**  
→ Your `GITHUB_TOKEN` is expired or missing `read:org` scope. Regenerate it at github.com/settings/tokens.

**GitHub API 404 on org repos**  
→ Token might not have access to the org. Ensure SSO is authorized if your org uses SAML SSO.

**Gemini API error / quota exceeded**  
→ Verify `GEMINI_API_KEY` is valid. Check quota at console.cloud.google.com. The indexer uses `EMBEDDING_BATCH_SIZE=50` with a semaphore of 5 concurrent requests to stay within rate limits.

**Frontend shows "Network Error"**  
→ Ensure backend is running on port 8000 and `NEXT_PUBLIC_API_URL=http://localhost:8000` is set in `frontend/.env.local`.

**Indexer runs but `--stats` shows 0 vectors**  
→ Check `REPOS_BASE_PATH` — repos must be cloned there first. Run `indexer.py --index` (not `--dry-run`).

**Chat returns "I could not find relevant information"**  
→ Repos haven't been indexed yet, or the question is about something not in the codebase. Run `indexer.py --stats` to confirm vectors exist. Try `indexer.py --search "your question"` to test retrieval directly.

## Getting Help

- `architecture.md` — system design and data flows
- `AGENT.md` — coding conventions for AI agents working in this repo
- http://localhost:8000/api/v1/docs — live API documentation
- Slack `#engineering-platform` for questions
