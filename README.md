# Wayfind — Placement & Career Assistant


An AI assistant that helps college students prepare for placements. Upload a
resume, find jobs and campus drives, see how well you match, learn what skills
you're missing, and practise for the interview. It is built from cooperating
AI agents, a retrieval (RAG) knowledge base and real MCP tool servers.

## Features

- **Resume analysis** — upload a PDF, DOCX or TXT resume; skills, education,
  projects and experience are extracted into an editable, saved profile.
- **Job search** — live web search (or a built-in fallback list) with an
  internship / full-time filter.
- **Match score and skill gaps** — a 0–100 match against any job, with matched
  and missing skills ranked by priority.
- **Learning roadmap** — a study plan for your missing skills, grounded in a
  curated knowledge base so it recommends real resources.
- **Interview prep** — role-specific questions with model answers.
- **Application tracker** — save jobs and move them through Saved, Applied,
  Interview, Offer and Rejected, with notes.
- **Placement calendar** — upcoming campus drives filtered by branch, CGPA,
  type and location, with eligibility checks and calendar export (.ics).
- **GitHub profile card** — turns your public repos into skill evidence.
- **AI chat assistant** — free-form questions routed to the right agent or tool.
- **Privacy controls** — Google sign-in, per-user data, and a one-click
  "Delete my data".

## How it works

```
React (Vite)  ──►  FastAPI  ──►  Agents (LangGraph / LangChain + Gemini)
                      │                │
                      │                ├──►  RAG: Chroma vector store
                      │                └──►  MCP tools: job search, GitHub
                      └──►  PostgreSQL (users, history, saved jobs)
```

- **Six agents:** resume, job matching, skill gap, learning, interview and an
  orchestrator. The orchestrator's LLM router decides which agent or tool a
  chat message needs.
- **MCP tools:** `search_jobs` and `analyze_github_profile` run as separate
  MCP servers over stdio. Agents call them through the MCP client, never
  directly.
- **RAG:** job matching, the roadmap and interview questions retrieve
  curated documents before generating, so answers are grounded.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Vitest, Playwright |
| Backend | FastAPI, Pydantic, LangGraph, LangChain, Google Gemini |
| Data | PostgreSQL (SQLite for quick local runs), SQLAlchemy, Alembic, Chroma |
| Tools | MCP (FastMCP), Tavily web search, GitHub API |
| Auth | Google Sign-In, JWT in an HTTP-only cookie |
| Deploy | Vercel (frontend), Render (backend), Neon (database) |

## Getting started

**Requirements:** Python 3.12, Node.js 22, and a free
[Gemini API key](https://aistudio.google.com/apikey). For sign-in you also
need a Google OAuth *Web application* client ID, with `http://localhost:5173`
added as an authorized JavaScript origin. Tavily and GitHub keys are optional.

### Run locally

```bash
# Backend (Windows: venv\Scripts\activate)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # set GOOGLE_API_KEY, GOOGLE_CLIENT_ID, JWT_SECRET_KEY
alembic upgrade head              # create the database tables
python -m app.rag.ingest          # load the knowledge base (once)
uvicorn app.main:app --reload --port 8000   # Windows: python run.py
```

```bash
# Frontend (in another terminal)
cd frontend
echo "VITE_GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com" > .env
npm install
npm run dev                       # http://localhost:5173
```

API docs are at `http://localhost:8000/docs`.

### Run with Docker

Put `VITE_GOOGLE_CLIENT_ID=...` in a `.env` file next to `docker-compose.yml`
and your keys in `backend/.env`, then:

```bash
docker compose up --build         # app at http://localhost:8080
```

Add `http://localhost:8080` to the Google authorized origins for this mode.

## Configuration

Set these in `backend/.env` (see `.env.example` for the full list):

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` | Gemini key (required) |
| `GOOGLE_CLIENT_ID` | Google sign-in client ID (required) |
| `JWT_SECRET_KEY` | Random 32+ character secret |
| `DATABASE_URL` | PostgreSQL URL (defaults to local SQLite) |
| `CORS_ORIGINS` | Frontend URL(s), no localhost in production |
| `TAVILY_API_KEY`, `GITHUB_TOKEN` | Optional: live job search, higher GitHub limits |

The frontend needs `VITE_GOOGLE_CLIENT_ID`.

## Testing and quality

```bash
cd backend  && ruff check . && mypy app && pytest -q
cd frontend && npm run check      # lint, format, typecheck, tests, build
cd frontend && npm run e2e        # Playwright end-to-end tests
```

GitHub Actions runs all of these, plus migration checks and Docker builds, on
every pull request.

## Deployment

The repo is set up for free-tier hosting: **Neon** for PostgreSQL, **Render**
for the backend (`render.yaml`, which runs migrations on start) and **Vercel**
for the frontend (`frontend/vercel.json` forwards `/api` to Render). Set
`CORS_ORIGINS` on Render to your Vercel URL and add that URL to your Google
OAuth origins. Note that Render's free tier sleeps when idle, so the first
request can take about a minute; the app shows a banner while it wakes up.

## Project structure

```
backend/
  app/agents/       resume, matching, skill gap, learning, interview, orchestrator
  app/api/          FastAPI routes, one file per resource
  app/mcp_tools/    MCP servers (job search, GitHub) and the client
  app/rag/          Chroma vector store and ingestion
  app/auth/         Google sign-in, JWT, database models
  alembic/          database migrations
  data/knowledge_base/   seed documents, sample jobs, campus drives
  tests/
frontend/
  src/components/   one component per screen
  src/api/client.js API client
  e2e/              Playwright tests
```

## Extending

- **Add a tool:** create a `FastMCP` server in `mcp_tools/`, add a client
  function in `mcp_client.py`, and call it from an agent or the orchestrator.
- **Add knowledge:** call `add_document(text, source, doc_type)` from
  `rag/vector_store.py`.
- **Add campus drives:** edit `backend/data/knowledge_base/campus_drives.json`
  (the bundled entries are samples).
