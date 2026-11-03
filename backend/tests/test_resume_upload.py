"""Edge cases for POST /api/resume/upload (the happy path and LLM failure are
covered in test_profile.py)."""

from unittest.mock import patch

from app.models.schemas import StudentProfile


def _upload(client, name, data, content_type="text/plain"):
    return client.post("/api/resume/upload", files={"file": (name, data, content_type)})


def test_unsupported_file_type_is_a_400(client):
    r = _upload(client, "photo.png", b"x", "image/png")

    assert r.status_code == 400
    assert "Unsupported file type" in r.json()["detail"]


def test_corrupt_docx_is_a_422(client):
    r = _upload(client, "cv.docx", b"definitely not a zip file")

    assert r.status_code == 422
    assert "Could not read this file" in r.json()["detail"]


def test_file_with_no_text_is_a_422(client):
    r = _upload(client, "cv.txt", b"   \n  ")

    assert r.status_code == 422
    assert "Could not extract text" in r.json()["detail"]


def test_oversized_file_is_a_413(client, monkeypatch):
    monkeypatch.setattr("app.api.routes_resume.MAX_UPLOAD_BYTES", 10)

    r = _upload(client, "cv.txt", b"x" * 11)

    assert r.status_code == 413
    assert "File too large" in r.json()["detail"]


def test_extracted_text_goes_to_the_agent_and_the_vector_store(client, test_user):
    profile = StudentProfile(name="Asha", skills=["Python", "FastAPI", "SQL"])
    with (
        patch("app.api.routes_resume.run_resume_agent", return_value=profile) as agent,
        patch("app.api.routes_resume.delete_user_documents") as delete_docs,
        patch("app.api.routes_resume.add_document") as add_doc,
    ):
        r = _upload(client, "cv.txt", b"Python developer")

    assert r.status_code == 200
    agent.assert_called_once_with("Python developer")
    # the previous resume is replaced, not appended to
    delete_docs.assert_called_once_with(test_user.id, "resume")
    add_doc.assert_called_once_with(
        "Python developer", "cv.txt", "resume", test_user.id
    )
    body = r.json()
    assert body["profile"]["name"] == "Asha"
    assert body["summary"] == ("Extracted 3 skills, 0 projects, 0 experience entries.")


def test_upload_requires_login():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).post(
        "/api/resume/upload", files={"file": ("cv.txt", b"x", "text/plain")}
    )
    assert r.status_code == 401
