from app.auth.models import SavedJob

JOB = {
    "id": "local-1",
    "title": "Software Engineer Intern",
    "company": "Kestrel Systems",
    "location": "Bengaluru, India",
    "description": "Python and SQL role",
    "url": "https://example.com/jobs/1",
    "source": "local",
}


def _save(client, job=JOB, **extra):
    return client.post("/api/saved-jobs", json={"job": job, **extra})


def test_list_is_empty_at_first(client):
    r = client.get("/api/saved-jobs")
    assert r.status_code == 200
    assert r.json() == []


def test_save_job_returns_the_tracker_row(client):
    r = _save(client)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "saved"
    assert body["notes"] == ""
    assert body["job"]["id"] == "local-1"
    assert body["job"]["title"] == "Software Engineer Intern"
    assert [row["id"] for row in client.get("/api/saved-jobs").json()] == [body["id"]]


def test_saving_the_same_job_twice_is_idempotent(client):
    first = _save(client).json()
    second = _save(client).json()
    assert first["id"] == second["id"]
    assert len(client.get("/api/saved-jobs").json()) == 1


def test_save_with_initial_status(client):
    r = _save(client, status="applied")
    assert r.json()["status"] == "applied"


def test_update_status_and_notes(client):
    saved = _save(client).json()

    r = client.patch(
        f"/api/saved-jobs/{saved['id']}",
        json={"status": "interview", "notes": "Referral from Priya"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "interview"
    assert r.json()["notes"] == "Referral from Priya"


def test_patch_with_only_notes_keeps_the_status(client):
    saved = _save(client, status="applied").json()

    r = client.patch(f"/api/saved-jobs/{saved['id']}", json={"notes": "call on Monday"})
    assert r.json()["status"] == "applied"
    assert r.json()["notes"] == "call on Monday"


def test_invalid_status_is_rejected(client):
    saved = _save(client).json()
    r = client.patch(f"/api/saved-jobs/{saved['id']}", json={"status": "ghosted"})
    assert r.status_code == 422
    assert _save(client, job={**JOB, "id": "x"}, status="nope").status_code == 422


def test_notes_length_is_limited(client):
    saved = _save(client).json()
    r = client.patch(f"/api/saved-jobs/{saved['id']}", json={"notes": "n" * 2001})
    assert r.status_code == 422


def test_delete_removes_the_job(client):
    saved = _save(client).json()
    assert client.delete(f"/api/saved-jobs/{saved['id']}").status_code == 204
    assert client.get("/api/saved-jobs").json() == []


def test_unknown_id_returns_404(client):
    assert (
        client.patch("/api/saved-jobs/99999", json={"status": "offer"}).status_code
        == 404
    )
    assert client.delete("/api/saved-jobs/99999").status_code == 404


def test_users_cannot_touch_each_others_saved_jobs(client, as_user, other_user):
    saved = _save(client).json()

    as_user(other_user)
    assert client.get("/api/saved-jobs").json() == []
    assert (
        client.patch(
            f"/api/saved-jobs/{saved['id']}", json={"status": "offer"}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/saved-jobs/{saved['id']}").status_code == 404


def test_long_description_is_truncated(client):
    saved = _save(client, job={**JOB, "description": "d" * 5000}).json()
    assert len(saved["job"]["description"]) == 4000


def test_save_limit_is_enforced(client, db_session, test_user):
    db_session.add_all(
        SavedJob(
            user_id=test_user.id,
            job_id=f"job-{i}",
            title="t",
            company="c",
            location="",
            description="",
            url="",
            source="local",
            status="saved",
            notes="",
        )
        for i in range(200)
    )
    db_session.commit()

    r = _save(client)
    assert r.status_code == 400
    assert "200" in r.json()["detail"]
