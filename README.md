# Wayfind — Placement & Career Assistant

![CI](https://github.com/pranavh-57/Placement-and-Career-Assistant/actions/workflows/ci.yml/badge.svg)

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
- **Accounts and privacy** — email and password sign-up with one-time-code
  (OTP) email verification, per-user data, and a one-click "Delete my data".

## How it works

```
React (Vite)  ──►  FastAPI  ──►  Agents (LangGraph / LangChain + Groq)
                      │                │
                      │                ├──►  RAG: Chroma vector store (Gemini embeddings)
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
- **Sign-up flow:** `register` stores a hashed password and a hashed 6-digit
  code and emails the code. The account is created only when `verify-otp`
  receives the correct code (10-minute expiry, 5 attempts, resend once a
  minute).

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Vitest, Playwright |
| Backend | FastAPI, Pydantic, LangGraph, LangChain |
| AI | Groq `openai/gpt-oss-120b` for the agents (Gemini also supported), Gemini embeddings for RAG |
| Data | PostgreSQL (SQLite for quick local runs), SQLAlchemy, Alembic, Chroma |
| Tools | MCP (FastMCP), Tavily web search, GitHub API |
| Auth | Email + password (bcrypt), OTP email verification via Resend, JWT in an HTTP-only cookie |
| Deploy | Vercel (frontend), Render (backend), Neon (database) |

## Getting started

**Requirements:** Python 3.12, Node.js 22, a free
[Groq API key](https://console.groq.com/keys) and a free
[Gemini API key](https://aistudio.google.com/apikey) (used for embeddings).
A [Resend](https://resend.com) key is optional locally: without it, the sign-up
code is printed in the backend log. Tavily and GitHub keys are optional.

### Run locally

```bash
# Backend (Windows: venv\Scripts\activate)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # set GROQ_API_KEY, GOOGLE_API_KEY, JWT_SECRET_KEY
alembic upgrade head              # create the database tables
python -m app.rag.ingest          # load the knowledge base (once)
uvicorn app.main:app --reload --port 8000   # Windows: python run.py
```

```bash
# Frontend (in another terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

API docs are at `http://localhost:8000/docs`.

**Signing up locally:** create an account in the app, then read the 6-digit
code from the backend terminal (look for `DEV MODE: verification code`). With a
`RESEND_API_KEY` set, the code is emailed instead.

### Run with Docker

Put your keys in `backend/.env`, then:

```bash
docker compose up --build         # app at http://localhost:8080
```

Containers read `.env` only when they start, so after editing it run
`docker compose up -d --force-recreate backend`.

## Configuration

Set these in `backend/.env` (see `.env.example` for the full list):

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `groq` (default) or `gemini` |
| `GROQ_API_KEY`, `GROQ_MODEL` | Groq key and model (`openai/gpt-oss-120b`) |
| `GOOGLE_API_KEY` | Gemini key, required for embeddings (and for the Gemini provider) |
| `JWT_SECRET_KEY` | Random 32+ character secret |
| `DATABASE_URL` | PostgreSQL URL (defaults to local SQLite) |
| `CORS_ORIGINS` | Frontend URL(s), no localhost in production |
| `RESEND_API_KEY`, `MAIL_FROM` | Sends OTP emails. Required in production |
| `TAVILY_API_KEY`, `GITHUB_TOKEN` | Optional: live job search, higher GitHub limits |

**Email sending:** without a verified domain, Resend only allows the sender
`onboarding@resend.dev` and only delivers to your own Resend account email.
To email any user, verify a domain at resend.com/domains and set
`MAIL_FROM="Wayfind <noreply@yourdomain.com>"`.

**Free-tier limits:** Groq's free plan allows about 30 requests a minute and
8,000 tokens a minute for `gpt-oss-120b`. The app keeps prompts small and
retries are limited; if you see 429 errors, wait a minute and try again.

## Testing and quality

```bash
cd backend  && ruff check . && mypy app && pytest -q
cd backend  && pytest --cov=app -q          # with coverage
cd frontend && npm run check                # lint, format, typecheck, tests, build
cd frontend && npm run test:coverage        # with coverage
cd frontend && npm run e2e                  # Playwright end-to-end tests
```

All LLM, MCP and email calls are mocked in tests, so they run offline. Run the
frontend commands from the `frontend` folder, and install the browser once for
the end-to-end tests with `npx playwright install chromium`.

GitHub Actions runs all of these, plus migration checks and Docker builds, on
every pull request.

## Deployment

The repo is set up for free-tier hosting: **Neon** for PostgreSQL, **Render**
for the backend (`render.yaml`, which runs migrations on start) and **Vercel**
for the frontend (`frontend/vercel.json` forwards `/api` to Render). In Render,
set `GROQ_API_KEY`, `GOOGLE_API_KEY`, `DATABASE_URL`, `RESEND_API_KEY`,
`MAIL_FROM` and `CORS_ORIGINS` (your Vercel URL). Note that Render's free tier
sleeps when idle, so the first request can take about a minute; the app shows a
banner while it wakes up. Render's free tier also blocks SMTP, which is why
emails are sent through Resend's HTTPS API.

## Project structure

```
backend/
  app/agents/       resume, matching, skill gap, learning, interview, orchestrator
  app/api/          FastAPI routes, one file per resource
  app/mcp_tools/    MCP servers (job search, GitHub) and the client
  app/rag/          Chroma vector store and ingestion
  app/auth/         password hashing, OTP, email sending, JWT, database models
  app/utils/        LLM client, structured output, text extraction
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
- **Switch the model:** set `LLM_PROVIDER` and the matching key in `backend/.env`.
