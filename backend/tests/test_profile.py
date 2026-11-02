from unittest.mock import patch

from app.auth.models import UserHistory
from app.models.schemas import StudentProfile


def test_get_profile_is_none_when_nothing_saved(client):
    r = client.get("/api/profile")
    assert r.status_code == 200
    assert r.json() == {"profile": None}


def test_put_then_get_roundtrip(client):
    body = {
        "name": "Asha",
        "email": "asha@example.com",
        "skills": ["Python", "SQL"],
        "projects": ["Chatbot"],
    }
    assert client.put("/api/profile", json=body).status_code == 200

    saved = client.get("/api/profile").json()["profile"]
    assert saved["name"] == "Asha"
    assert saved["skills"] == ["Python", "SQL"]
    assert saved["projects"] == ["Chatbot"]


def test_put_replaces_instead_of_duplicating(client, db_session, test_user):
    client.put("/api/profile", json={"skills": ["Python"]})
    client.put("/api/profile", json={"skills": ["Go"]})

    rows = (
        db_session.query(UserHistory)
        .filter(UserHistory.user_id == test_user.id, UserHistory.kind == "profile")
        .all()
    )
    assert len(rows) == 1
    assert client.get("/api/profile").json()["profile"]["skills"] == ["Go"]


def test_put_cleans_up_skills_and_projects(client):
    body = {
        "skills": ["  Python ", "", "   ", "x" * 100],
        "projects": ["  Chatbot  ", "", "p" * 400],
    }
    client.put("/api/profile", json=body)

    saved = client.get("/api/profile").json()["profile"]
    assert saved["skills"] == ["Python", "x" * 60]
    assert saved["projects"] == ["Chatbot", "p" * 300]


def test_put_caps_list_sizes(client):
    body = {
        "skills": [f"skill-{i}" for i in range(150)],
        "projects": [f"project-{i}" for i in range(50)],
    }
    client.put("/api/profile", json=body)

    saved = client.get("/api/profile").json()["profile"]
    assert len(saved["skills"]) == 100
    assert len(saved["projects"]) == 30


def test_raw_resume_text_is_never_stored(client):
    client.put("/api/profile", json={"skills": ["Python"], "raw_text": "SECRET CV"})

    saved = client.get("/api/profile").json()["profile"]
    assert "raw_text" not in saved
    assert "SECRET CV" not in str(saved)


def test_profile_is_private_to_each_user(client, as_user, other_user):
    client.put("/api/profile", json={"skills": ["Python"]})

    as_user(other_user)
    assert client.get("/api/profile").json() == {"profile": None}


def test_profile_does_not_show_up_in_history(client):
    client.put("/api/profile", json={"skills": ["Python"]})
    assert client.get("/api/history").json() == []


def test_resume_upload_saves_the_profile(client):
    profile = StudentProfile(name="Asha", skills=["Python", "FastAPI"])
    with (
        patch("app.api.routes_resume.extract_text", return_value="Resume text"),
        patch("app.api.routes_resume.run_resume_agent", return_value=profile),
        patch("app.api.routes_resume.delete_user_documents"),
        patch("app.api.routes_resume.add_document"),
    ):
        r = client.post(
            "/api/resume/upload",
            files={"file": ("cv.txt", b"x", "text/plain")},
        )

    assert r.status_code == 200
    saved = client.get("/api/profile").json()["profile"]
    assert saved["skills"] == ["Python", "FastAPI"]


def test_failed_upload_keeps_the_previous_profile(client):
    client.put("/api/profile", json={"name": "Old", "skills": ["Python"]})
    with (
        patch("app.api.routes_resume.extract_text", return_value="Resume text"),
        patch(
            "app.api.routes_resume.run_resume_agent",
            side_effect=Exception("LLM down"),
        ),
    ):
        r = client.post(
            "/api/resume/upload",
            files={"file": ("cv.txt", b"x", "text/plain")},
        )

    assert r.status_code == 502
    assert client.get("/api/profile").json()["profile"]["name"] == "Old"
