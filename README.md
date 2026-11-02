# Wayfind — Placement & Career Assistant

An agentic AI assistant for college placements: upload a resume, search jobs,
get a match score, find skill gaps, get a learning roadmap, and practice
interviews — all driven by six cooperating agents, a RAG knowledge base, and
real MCP tool servers.

## Architecture

```
placement-assistant/
├── backend/                  FastAPI + LangGraph + LangChain + Chroma
│   ├── app/
│   │   ├── agents/           6 agents + LangGraph orchestrator graph
│   │   │   ├── resume_agent.py
│   │   │   ├── job_matching_agent.py
│   │   │   ├── skill_gap_agent.py
│   │   │   ├── learning_agent.py
│   │   │   ├── interview_agent.py
│   │   │   ├── orchestrator.py   ← LangGraph pipeline + chat intent router
│   │   │   └── state.py
│   │   ├── rag/               Chroma vector store + ingestion
│   │   ├── mcp_tools/         Real MCP servers (stdio) + client wrapper
│   │   │   ├── job_search_server.py   ← MCP tool: search_jobs
│   │   │   ├── github_server.py       ← MCP tool: analyze_github_profile
│   │   │   └── mcp_client.py          ← spawns the servers, calls tools
│   │   ├── api/                FastAPI routes, one file per resource
│   │   ├── models/schemas.py   Shared Pydantic models
│   │   ├── utils/               PDF parsing, LLM client, JSON extraction
│   │   ├── config.py
│   │   └── main.py
│   ├── data/knowledge_base/    Seed RAG documents + local job fallback
│   ├── requirements.txt
│   └── .env.example
└── frontend/                  React + Vite + Tailwind CSS
    └── src/
        ├── components/         Sidebar, ResumeUpload,
        │                       JobSearch, MatchScore, LearningRoadmap,
        │                       InterviewPrep, Overview
        ├── api/client.js        Axios client for every backend endpoint
        └── App.jsx
```

### Why this is genuinely agentic (not one LLM call)

- **Orchestrator Agent** (`agents/orchestrator.py`) does two things:
  1. Runs a **LangGraph** `StateGraph` for the full pipeline
     (`search_jobs → match → skill_gap → learning → interview`), where each
     node is a separate agent function and state is threaded and logged
     between them.
  2. For free-form chat, an LLM **router** reads the user's message and
     decides which single agent or MCP tool actually applies
     (`job_search`, `github_analysis`, `skill_gap`, `learning`,
     `interview`, or a RAG-grounded answer) — this is a real routing
     decision, not a keyword `if/else`.
- **MCP tools are real MCP servers.** `job_search_server.py` and
  `github_server.py` are built with `FastMCP`, run as separate stdio
  subprocesses, and are called through the official `mcp` client SDK
  (`mcp_client.py`). Agents never call the GitHub API or search API
  directly — they go through the MCP tool boundary.
- **RAG is used for retrieval before generation**, not appended as an
  afterthought: Job Matching pulls similar job-description context to
  calibrate scoring; Learning Recommendation retrieves real curated
  resources before asking the LLM to organize them into a roadmap (so it
  isn't inventing course names); Interview generation retrieves
  interview-prep material for the specific role family first.

## Prerequisites

- Python 3.12+
- Node.js 18+
- A free **Google Gemini API key**: https://aistudio.google.com/apikey

Optional (the app works without these, with graceful fallbacks):
- **Tavily API key** (https://tavily.com) — enables live web job search.
  Without it, the job-search MCP tool uses a curated local listings file
  (`backend/data/knowledge_base/sample_jobs.json`).
- **GitHub token** — raises the GitHub API rate limit from 60 to 5000
  req/hr. Public profile analysis works fine unauthenticated at low volume.

## Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# then edit .env and set GOOGLE_API_KEY=... (required)
# TAVILY_API_KEY and GITHUB_TOKEN are optional

# Seed the RAG knowledge base (career guides, interview prep, learning resources)
python -m app.rag.ingest

# Run the API
uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. Check `GET /api/health` to confirm your keys
are picked up.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard is now live at `http://localhost:5173` (proxies `/api` to
`http://localhost:8000`, configured in `vite.config.js`).

## Using it

1. **Resume & Profile** — upload a PDF resume. The Resume Agent extracts
   skills, education, projects, and experience, and the resume text is
   indexed into the RAG knowledge base.
2. **Job Search** — search for roles. Routed through the `search_jobs` MCP
   tool (live web search via Tavily, or the local fallback listings).
   Select a job to analyze it.
3. **Match & Skill Gap** — runs the Job Matching Agent (0–100 score,
   matched/missing skills) and the Skill Gap Agent (priority-ordered gaps).
4. **Learning Roadmap** — the Learning Recommendation Agent turns your
   prioritized skill gaps into a roadmap grounded in the RAG knowledge
   base.
5. **Interview Prep** — the Interview Agent generates role-specific
   questions and scores your typed answers with concrete feedback.
6. **Overview** — "Run full workflow" chains all of the above from a single
   job-role query; the chat box routes free-form questions through the
   Orchestrator (try "find me ML internships" or "analyze github user
   torvalds").

Watch the **Agent Activity** panel on the right at any time — it's a live
trace of which agent acted, what it did, and (for MCP calls) which tool
was actually invoked.

## Extending it

- **Add an MCP tool**: create a new `FastMCP` server under `mcp_tools/`,
  add a client function in `mcp_client.py`, and call it from an agent or
  from the orchestrator's router.
- **Add a document type to RAG**: call `add_document(text, source,
  doc_type)` from `rag/vector_store.py` — the interview, learning, and
  matching agents already filter retrieval by `doc_type`.
- **Calendar/task integration** (optional per the original spec): add a
  third MCP server following the same `FastMCP` + stdio pattern as
  `job_search_server.py`, then wire it into the orchestrator's router.

## Notes on Gemini models

`.env.example` defaults to `gemini-3.8-flash` for chat and
`models/gemini-embedding-001` for embeddings — both fast and inexpensive.
Swap `GEMINI_MODEL` for a stronger model if you want higher-quality
extraction/reasoning at higher latency/cost.
