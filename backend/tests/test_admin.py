import asyncio
import json

import pytest
from starlette.requests import Request

from app.admin import tracking
from app.admin.models import AgentRun, AuditLog
from app.auth.models import User, UserHistory
from app.config import settings
from tests.conftest import TestSessionLocal


@pytest.fixture()
def admin(db_session, test_user):
    test_user.is_admin = True
    db_session.commit()
    return test_user


def test_non_admin_is_forbidden(client):
    assert client.get("/api/admin/overview").status_code == 403


def test_overview_shape(client, admin):
    r = client.get("/api/admin/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["students"] == 0  # the admin is not counted as a student
    assert len(body["registrations"]) == 14


def test_student_status_and_audit(client, admin, other_user, db_session):
    r = client.patch(
        f"/api/admin/students/{other_user.id}/status", json={"status": "suspended"}
    )
    assert r.status_code == 200
    db_session.refresh(other_user)
    assert other_user.status == "suspended"
    assert db_session.query(AuditLog).filter_by(action="student.status").count() == 1


def test_student_detail_hides_resume_content(client, admin, other_user, db_session):
    db_session.add(
        UserHistory(
            user_id=other_user.id,
            kind="profile",
            payload=json.dumps({"skills": ["Python"], "raw_text": "SECRET RESUME"}),
        )
    )
    db_session.commit()
    r = client.get(f"/api/admin/students/{other_user.id}")
    assert r.status_code == 200
    assert r.json()["skills"] == ["Python"]
    assert "SECRET RESUME" not in r.text
    assert db_session.query(AuditLog).filter_by(action="student.view").count() == 1


def test_cannot_manage_admins_as_students(client, admin):
    assert client.get(f"/api/admin/students/{admin.id}").status_code == 404


def test_csv_neutralises_formulas(client, admin, db_session):
    db_session.add(
        User(email="x@example.com", name="=HYPERLINK(1)", password_hash=None)
    )
    db_session.commit()
    r = client.get("/api/admin/students/export.csv")
    assert r.status_code == 200
    assert "'=HYPERLINK(1)" in r.text


def test_suspended_user_is_blocked(db_session, other_user):
    from fastapi import HTTPException

    from app.auth.dependencies import get_current_user
    from app.auth.security import create_access_token

    other_user.status = "suspended"
    db_session.commit()
    token = create_access_token(other_user.id, other_user.email)

    req = Request(
        {
            "type": "http",
            "headers": [(b"cookie", f"access_token={token}".encode())],
        }
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(req, None, db_session)
    assert exc.value.status_code == 403


def test_drive_crud_matches_student_endpoint(client, admin, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    (tmp_path / "campus_drives.json").write_text("[]")
    body = {
        "company": "Acme",
        "role": "Engineer",
        "type": "full-time",
        "date": "2999-01-01",
        "branches": ["CSE"],
        "min_cgpa": 7,
    }
    created = client.post("/api/admin/drives", json=body)
    assert created.status_code == 201
    drive_id = created.json()["id"]
    # The existing student-facing endpoint must still work with admin-written data.
    student_view = client.get("/api/campus/drives")
    assert student_view.status_code == 200
    assert [d["id"] for d in student_view.json()] == [drive_id]

    body["role"] = "Senior Engineer"
    assert client.put(f"/api/admin/drives/{drive_id}", json=body).status_code == 200
    assert client.delete(f"/api/admin/drives/{drive_id}").status_code == 204
    assert client.get("/api/admin/drives").json() == []


def test_tracking_records_type_only(monkeypatch, db_session):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setattr(tracking, "SessionLocal", TestSessionLocal)

    @tracking.track_agent("resume")
    def boom():
        raise ValueError("contains SECRET RESUME TEXT")

    @tracking.track_agent("resume")
    def fine():
        return 1

    with pytest.raises(ValueError):
        boom()
    assert fine() == 1
    runs = db_session.query(AgentRun).order_by(AgentRun.id).all()
    assert [r.status for r in runs] == ["failed", "success"]
    assert runs[0].error == "ValueError"
    assert "SECRET" not in runs[0].error


def test_tracking_awaits_async(monkeypatch, db_session):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setattr(tracking, "SessionLocal", TestSessionLocal)

    @tracking.track_mcp("search_jobs")
    async def tool():
        return {"error": "x"}

    assert asyncio.run(tool()) == {"error": "x"}
    run = db_session.query(AgentRun).one()
    assert (run.kind, run.status) == ("mcp", "failed")
