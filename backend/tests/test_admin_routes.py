import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.admin.models import AgentRun, AuditLog
from app.auth.models import SavedJob, User, UserHistory
from app.config import settings


@pytest.fixture()
def admin(db_session, test_user):
    test_user.is_admin = True
    db_session.commit()
    return test_user


@pytest.fixture()
def drives_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    return tmp_path


def _write_drives(path, items):
    (path / "campus_drives.json").write_text(json.dumps(items))


def _saved_job(user, status="saved", job_id="j1"):
    return SavedJob(
        user_id=user.id, job_id=job_id, title="Intern", company="Acme",
        location="", description="", url="", source="local", status=status, notes="",
    )


DRIVE = {
    "company": "Acme", "role": "Engineer", "type": "full-time",
    "date": "2999-01-01", "branches": ["CSE"], "min_cgpa": 7,
}


# ------------------------------------------------------------ access control


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/overview", "/api/admin/students", "/api/admin/drives",
        "/api/admin/agents", "/api/admin/runs", "/api/admin/kb",
        "/api/admin/mcp", "/api/admin/audit",
    ],
)
def test_every_admin_read_is_forbidden_for_students(client, path):
    assert client.get(path).status_code == 403


# ------------------------------------------------------------------ overview


def test_overview_counts_everything(client, admin, other_user, db_session, drives_dir):
    _write_drives(
        drives_dir,
        [
            {"id": "drive-1", "company": "A", "date": "2999-01-01"},
            {"id": "drive-2", "company": "B", "date": "2000-01-01"},
        ],
    )
    other_user.last_login_at = datetime.now(UTC)
    db_session.add_all(
        [
            UserHistory(user_id=other_user.id, kind="profile", payload="{}"),
            _saved_job(other_user, "applied"),
            AgentRun(kind="agent", name="resume", status="success", duration_ms=10),
            AgentRun(kind="agent", name="resume", status="failed", duration_ms=20, error="ValueError"),
            AgentRun(kind="mcp", name="search_jobs", status="success", duration_ms=5),
        ]
    )
    db_session.commit()

    body = client.get("/api/admin/overview").json()

    stats = body["stats"]
    assert stats["students"] == 1
    assert stats["active_students"] == 1
    assert stats["resumes"] == 1
    assert stats["saved_jobs"] == 1
    assert stats["active_drives"] == 1
    assert stats["ai_interactions"] == 2  # MCP calls are not agent interactions
    assert stats["agent_failures"] == 1
    assert stats["agent_success_rate"] == 50.0
    assert body["agent_usage"] == [{"name": "resume", "count": 2}]
    pipeline = {p["status"]: p["count"] for p in body["placement_pipeline"]}
    assert pipeline["applied"] == 1 and pipeline["saved"] == 0
    assert body["activity"][-1]["count"] == 2
    assert body["registrations"][-1]["count"] == 1


def test_overview_with_no_data_has_no_success_rate(client, admin, drives_dir):
    stats = client.get("/api/admin/overview").json()["stats"]
    assert stats["agent_success_rate"] is None
    assert stats["active_drives"] == 0


def test_overview_days_are_validated(client, admin, drives_dir):
    assert client.get("/api/admin/overview?days=3").status_code == 422
    body = client.get("/api/admin/overview?days=7").json()
    assert len(body["registrations"]) == 7


# ------------------------------------------------------------------ students


def _two_students(db_session):
    a = User(email="asha@x.com", name="Asha", password_hash=None)
    b = User(email="ravi@y.com", name="Ravi", password_hash=None, status="suspended")
    db_session.add_all([a, b])
    db_session.commit()
    return a, b


def test_students_search_filter_and_paginate(client, admin, db_session):
    _two_students(db_session)

    assert client.get("/api/admin/students").json()["total"] == 2
    assert client.get("/api/admin/students?q=ash").json()["total"] == 1
    assert client.get("/api/admin/students?q=y.com").json()["total"] == 1
    assert client.get("/api/admin/students?status=suspended").json()["total"] == 1
    assert client.get("/api/admin/students?status=banned").status_code == 422

    page2 = client.get("/api/admin/students?page=2&page_size=1").json()
    assert page2["total"] == 2 and len(page2["items"]) == 1

    future = client.get("/api/admin/students?since=2999-01-01T00:00:00").json()
    assert future["total"] == 0
    past = client.get("/api/admin/students?since=2000-01-01T00:00:00").json()
    assert past["total"] == 2


def test_students_export_respects_filters_and_is_audited(client, admin, db_session):
    _two_students(db_session)
    r = client.get("/api/admin/students/export.csv?status=suspended")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0] == "id,email,name,status,created_at,last_login_at"
    assert len(lines) == 2 and "ravi@y.com" in lines[1]
    entry = db_session.query(AuditLog).filter_by(action="students.export").one()
    assert entry.detail == "1 rows"


def test_student_detail_lists_activity_and_saved_jobs(client, admin, other_user, db_session):
    db_session.add_all(
        [
            UserHistory(user_id=other_user.id, kind="profile",
                        payload=json.dumps({"skills": ["Python", "SQL"]})),
            UserHistory(user_id=other_user.id, kind="analysis", payload="{}"),
            _saved_job(other_user, "offer"),
        ]
    )
    db_session.commit()

    body = client.get(f"/api/admin/students/{other_user.id}").json()

    assert body["skills"] == ["Python", "SQL"]
    assert {a["kind"] for a in body["activity"]} == {"profile", "analysis"}
    assert body["saved_jobs"][0]["status"] == "offer"
    assert "payload" not in json.dumps(body)


def test_unknown_student_is_404_everywhere(client, admin):
    assert client.get("/api/admin/students/9999").status_code == 404
    r = client.patch("/api/admin/students/9999/status", json={"status": "active"})
    assert r.status_code == 404
    assert client.delete("/api/admin/students/9999").status_code == 404


def test_invalid_status_is_rejected(client, admin, other_user):
    r = client.patch(f"/api/admin/students/{other_user.id}/status", json={"status": "banned"})
    assert r.status_code == 422


def test_student_can_be_reactivated(client, admin, other_user, db_session):
    other_user.status = "suspended"
    db_session.commit()
    r = client.patch(f"/api/admin/students/{other_user.id}/status", json={"status": "active"})
    assert r.status_code == 200 and r.json()["status"] == "active"


def test_delete_student_removes_data_and_vectors(client, admin, other_user, db_session):
    uid = other_user.id
    db_session.add_all(
        [UserHistory(user_id=uid, kind="profile", payload="{}"), _saved_job(other_user)]
    )
    db_session.commit()
    clear = MagicMock()
    with (
        patch("app.admin.routes.delete_user_documents") as delete_docs,
        patch("app.admin.routes.clear_user", clear),
    ):
        r = client.delete(f"/api/admin/students/{uid}")

    assert r.status_code == 204
    assert db_session.query(User).filter_by(id=uid).count() == 0
    assert db_session.query(UserHistory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SavedJob).filter_by(user_id=uid).count() == 0
    assert {c.args[1] for c in delete_docs.call_args_list} == {"resume", "user_note"}
    clear.assert_called_once_with(uid)
    assert db_session.query(AuditLog).filter_by(action="student.delete").count() == 1


def test_delete_student_stops_if_vectors_cannot_be_removed(client, admin, other_user, db_session):
    with patch("app.admin.routes.delete_user_documents", side_effect=RuntimeError("chroma")):
        r = client.delete(f"/api/admin/students/{other_user.id}")
    assert r.status_code == 502
    assert db_session.query(User).filter_by(id=other_user.id).count() == 1


# -------------------------------------------------------------------- drives


def test_drives_list_is_empty_without_a_file(client, admin, drives_dir):
    assert client.get("/api/admin/drives").json() == []


def test_drive_ids_increment_and_list_is_sorted(client, admin, drives_dir):
    _write_drives(drives_dir, [{"id": "drive-5", "company": "Old", "date": "2999-06-01"}])
    first = client.post("/api/admin/drives", json={**DRIVE, "date": "2999-03-01"})
    assert first.json()["id"] == "drive-6"
    listing = client.get("/api/admin/drives").json()
    assert [d["date"] for d in listing] == ["2999-03-01", "2999-06-01"]


def test_drive_ids_start_at_one_when_existing_ids_are_not_numeric(client, admin, drives_dir):
    _write_drives(drives_dir, [{"id": "abc", "company": "X", "date": "2999-01-01"}])
    assert client.post("/api/admin/drives", json=DRIVE).json()["id"] == "drive-1"


def test_drive_optional_fields_round_trip(client, admin, drives_dir):
    _write_drives(drives_dir, [])
    body = {**DRIVE, "apply_by": "2999-01-01", "url": "https://acme.test/apply"}
    created = client.post("/api/admin/drives", json=body).json()
    assert created["apply_by"] == "2999-01-01"
    without = client.post("/api/admin/drives", json=DRIVE).json()
    assert "apply_by" not in without


@pytest.mark.parametrize(
    "patch_body",
    [{"url": "ftp://nope"}, {"min_cgpa": 11}, {"type": "contract"}, {"company": ""}, {"date": "tomorrow"}],
)
def test_invalid_drives_are_rejected(client, admin, drives_dir, patch_body):
    _write_drives(drives_dir, [])
    assert client.post("/api/admin/drives", json={**DRIVE, **patch_body}).status_code == 422


def test_update_and_delete_unknown_drive_are_404(client, admin, drives_dir):
    _write_drives(drives_dir, [])
    assert client.put("/api/admin/drives/nope", json=DRIVE).status_code == 404
    assert client.delete("/api/admin/drives/nope").status_code == 404


def test_updating_a_drive_keeps_its_id_and_audits(client, admin, drives_dir, db_session):
    _write_drives(drives_dir, [])
    drive_id = client.post("/api/admin/drives", json=DRIVE).json()["id"]
    r = client.put(f"/api/admin/drives/{drive_id}", json={**DRIVE, "role": "Lead"})
    assert r.json()["id"] == drive_id and r.json()["role"] == "Lead"
    actions = [a.action for a in db_session.query(AuditLog).order_by(AuditLog.id)]
    assert actions == ["drive.create", "drive.update"]


# -------------------------------------------------------------------- agents


def test_agents_summary_lists_every_agent(client, admin, db_session):
    db_session.add_all(
        [
            AgentRun(kind="agent", name="resume", status="success", duration_ms=10),
            AgentRun(kind="agent", name="resume", status="failed", duration_ms=30),
            AgentRun(kind="mcp", name="search_jobs", status="failed", duration_ms=99),
        ]
    )
    db_session.commit()

    rows = {r["name"]: r for r in client.get("/api/admin/agents").json()}

    assert set(rows) == {"resume", "job_matching", "skill_gap", "learning", "interview", "orchestrator"}
    assert rows["resume"]["runs"] == 2 and rows["resume"]["failed"] == 1
    assert rows["resume"]["success_rate"] == 50.0
    assert rows["resume"]["avg_ms"] == 20
    assert rows["resume"]["last_run"] is not None
    assert rows["learning"]["runs"] == 0
    assert rows["learning"]["success_rate"] is None
    assert rows["learning"]["avg_ms"] is None


def test_runs_can_be_filtered(client, admin, db_session):
    db_session.add_all(
        [
            AgentRun(kind="agent", name="resume", status="success", duration_ms=1),
            AgentRun(kind="agent", name="learning", status="failed", duration_ms=2),
            AgentRun(kind="mcp", name="search_jobs", status="success", duration_ms=3),
        ]
    )
    db_session.commit()

    agents = client.get("/api/admin/runs").json()
    assert {r["name"] for r in agents} == {"resume", "learning"}
    assert [r["name"] for r in client.get("/api/admin/runs?kind=mcp").json()] == ["search_jobs"]
    by_name = client.get("/api/admin/runs?name=learning").json()
    assert [r["status"] for r in by_name] == ["failed"]
    failed = client.get("/api/admin/runs?status=failed").json()
    assert [r["name"] for r in failed] == ["learning"]
    assert len(client.get("/api/admin/runs?limit=1").json()) == 1
    assert client.get("/api/admin/runs?kind=bogus").status_code == 422


# ----------------------------------------------------------- knowledge base


class FakeCollection:
    def __init__(self, metadatas=None, fail=False):
        self.metadatas = metadatas or []
        self.fail = fail
        self.get_args = None
        self.deleted = []

    def get(self, where=None, include=None):
        if self.fail:
            raise RuntimeError("chroma down")
        self.get_args = {"where": where, "include": include}
        return {"metadatas": self.metadatas}

    def delete(self, where=None):
        if self.fail:
            raise RuntimeError("chroma down")
        self.deleted.append(where)


@pytest.fixture()
def fake_kb(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr("app.admin.routes._collection", lambda: fake)
    return fake


PRIVATE_FILTER = {"doc_type": {"$nin": ["resume", "user_note"]}}


def test_kb_list_groups_chunks_by_source_and_hides_private_docs(client, admin, fake_kb):
    fake_kb.metadatas = [
        {"source": "a.txt", "doc_type": "career_guide"},
        {"source": "a.txt", "doc_type": "career_guide"},
        {"source": "b.md", "doc_type": "interview_prep"},
        None,
    ]
    body = client.get("/api/admin/kb").json()
    assert body["documents"] == 3 and body["chunks"] == 4
    assert [d["source"] for d in body["items"]] == ["a.txt", "b.md", "unknown"]
    assert body["items"][0]["chunks"] == 2
    assert fake_kb.get_args["where"] == PRIVATE_FILTER


def test_kb_list_reports_an_unavailable_store(client, admin, fake_kb):
    fake_kb.fail = True
    r = client.get("/api/admin/kb")
    assert r.status_code == 503 and "RuntimeError" in r.json()["detail"]


def _upload(client, name="guide.txt", content=b"hello world", doc_type="career_guide"):
    return client.post(
        f"/api/admin/kb?doc_type={doc_type}",
        files={"file": (name, content, "application/octet-stream")},
    )


def test_kb_upload_indexes_and_replaces_by_source(client, admin, fake_kb, db_session):
    with patch("app.rag.vector_store.add_document", return_value=3) as add:
        r = _upload(client)
    assert r.status_code == 201
    assert r.json() == {"source": "guide.txt", "doc_type": "career_guide", "chunks": 3}
    add.assert_called_once_with("hello world", "guide.txt", "career_guide", None, 1200, 150, True)
    # old chunks are removed first, and only from shared documents
    assert fake_kb.deleted == [{"$and": [PRIVATE_FILTER, {"source": "guide.txt"}]}]
    assert db_session.query(AuditLog).filter_by(action="kb.upload").count() == 1


def test_kb_upload_accepts_markdown(client, admin, fake_kb):
    with patch("app.rag.vector_store.add_document", return_value=1) as add:
        r = _upload(client, name="notes.md", content=b"# Title")
    assert r.status_code == 201
    assert add.call_args.args[0] == "# Title"


def test_kb_upload_rejects_bad_input(client, admin, fake_kb, monkeypatch):
    assert _upload(client, doc_type="resume").status_code == 400
    assert _upload(client, name="virus.exe").status_code == 400
    assert _upload(client, name="noextension").status_code == 400
    assert _upload(client, content=b"   ").status_code == 422

    monkeypatch.setattr("app.admin.routes.MAX_UPLOAD", 5)
    assert _upload(client, content=b"123456").status_code == 413


def test_kb_upload_reports_unreadable_files_and_index_failures(client, admin, fake_kb):
    with patch("app.utils.text_extraction.extract_text", side_effect=ValueError("corrupt")):
        r = _upload(client)
    assert r.status_code == 422 and "corrupt" in r.json()["detail"]

    with patch("app.rag.vector_store.add_document", side_effect=RuntimeError("x")):
        r = _upload(client)
    assert r.status_code == 502


def test_kb_delete_only_touches_shared_documents(client, admin, fake_kb, db_session):
    r = client.delete("/api/admin/kb?source=guide.txt")
    assert r.status_code == 204
    assert fake_kb.deleted == [{"$and": [PRIVATE_FILTER, {"source": "guide.txt"}]}]
    assert db_session.query(AuditLog).filter_by(action="kb.delete").count() == 1


def test_kb_delete_reports_an_unavailable_store(client, admin, fake_kb):
    fake_kb.fail = True
    assert client.delete("/api/admin/kb?source=x").status_code == 503


def test_kb_reseed_success_and_failure(client, admin, db_session):
    with patch("app.rag.ingest.ingest_seed_kb", return_value={"ingested": 2}):
        r = client.post("/api/admin/kb/reseed")
    assert r.status_code == 200 and r.json() == {"ingested": 2}
    assert db_session.query(AuditLog).filter_by(action="kb.reseed").count() == 1

    with patch("app.rag.ingest.ingest_seed_kb", side_effect=RuntimeError("no key")):
        assert client.post("/api/admin/kb/reseed").status_code == 502


# ----------------------------------------------------------------------- mcp


def test_mcp_health_is_inferred_from_the_latest_call(client, admin, db_session):
    db_session.add_all(
        [
            AgentRun(kind="mcp", name="search_jobs", status="success", duration_ms=10),
            AgentRun(kind="mcp", name="search_jobs", status="failed", duration_ms=30),
            AgentRun(kind="mcp", name="analyze_github_profile", status="success", duration_ms=50),
        ]
    )
    db_session.commit()

    servers = {s["id"]: s for s in client.get("/api/admin/mcp").json()}

    assert servers["job_search"]["health"] == "degraded"
    tool = servers["job_search"]["tools"][0]
    assert tool["calls_7d"] == 2 and tool["failed_7d"] == 1
    assert tool["avg_ms"] == 20 and tool["last_status"] == "failed"
    assert servers["github"]["health"] == "healthy"


def test_mcp_health_is_unknown_without_calls(client, admin):
    servers = client.get("/api/admin/mcp").json()
    assert {s["health"] for s in servers} == {"unknown"}
    assert servers[0]["tools"][0]["avg_ms"] is None


def test_mcp_ignores_calls_older_than_a_week(client, admin, db_session):
    db_session.add(
        AgentRun(
            kind="mcp", name="search_jobs", status="failed", duration_ms=1,
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
    )
    db_session.commit()
    servers = {s["id"]: s for s in client.get("/api/admin/mcp").json()}
    assert servers["job_search"]["tools"][0]["calls_7d"] == 0


# --------------------------------------------------------------------- audit


def test_audit_log_filters_by_action_prefix(client, admin, other_user, db_session):
    client.patch(f"/api/admin/students/{other_user.id}/status", json={"status": "suspended"})
    client.get(f"/api/admin/students/{other_user.id}")
    with patch("app.rag.ingest.ingest_seed_kb", return_value={}):
        client.post("/api/admin/kb/reseed")

    everything = client.get("/api/admin/audit").json()
    assert everything[0]["action"] == "kb.reseed"  # newest first
    students = client.get("/api/admin/audit?action=student").json()
    assert {e["action"] for e in students} == {"student.status", "student.view"}
    assert students[0]["admin"] == admin.email
    assert len(client.get("/api/admin/audit?limit=1").json()) == 1
    assert client.get("/api/admin/audit?limit=0").status_code == 422
