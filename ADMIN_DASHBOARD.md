# Admin dashboard

1. `cd backend && alembic upgrade head`
2. Promote yourself: `python -m scripts.make_admin you@college.edu`
3. Sign in, open `#/admin` (or the "Admin dashboard" link in the sidebar).

Notes
- Agent and MCP tracking stores name, outcome, duration and the exception class only.
- Drives are edited in `data/knowledge_base/campus_drives.json`, the file the student
  calendar reads. On hosts with an ephemeral disk (e.g. Render) edits are lost on redeploy.
- Suspending a student blocks login and every authenticated request.
