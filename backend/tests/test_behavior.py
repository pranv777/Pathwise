import uuid
from unittest.mock import AsyncMock, patch

import pytest
from langchain_chroma import Chroma
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.auth.models import UserHistory
from app.rag import vector_store
from app.utils.llm import extract_json


@pytest.fixture()
def kb(monkeypatch):
    """Real Chroma (in-memory) with deterministic fake embeddings: no API calls."""
    store = Chroma(
        collection_name=f"t_{uuid.uuid4().hex}",
        embedding_function=DeterministicFakeEmbedding(size=64),
    )
    monkeypatch.setattr(vector_store, "_store", store)
    return store


def test_resume_isolated_per_user(kb):
    vector_store.add_document("alice python resume " * 30, "a.pdf", "resume", user_id=1)
    vector_store.add_document("bob java resume " * 30, "b.pdf", "resume", user_id=2)
    vector_store.add_document("shared career advice " * 30, "kb", "career_guide")

    mine = vector_store.search("resume", k=10, doc_type="resume", user_id=1)
    assert mine and all(d.metadata["user_id"] == 1 for d, _ in mine)

    assert (
        vector_store.search("resume", k=10, doc_type="resume") == []
    )  # unscoped refused

    shared = vector_store.search("resume", k=10)
    assert shared and all(d.metadata["doc_type"] != "resume" for d, _ in shared)


def test_resume_reupload_replaces_old(kb):
    vector_store.add_document("old resume " * 30, "r.pdf", "resume", user_id=1)
    vector_store.delete_user_documents(1, "resume")
    vector_store.add_document("new resume " * 30, "r.pdf", "resume", user_id=1)
    hits = vector_store.search("resume", k=20, doc_type="resume", user_id=1)
    assert hits and all("new" in d.page_content for d, _ in hits)


def test_seed_ingest_is_idempotent(kb):
    vector_store.add_document("guide text " * 30, "g", "career_guide", stable_ids=True)
    first = kb._collection.count()
    vector_store.add_document("guide text " * 30, "g", "career_guide", stable_ids=True)
    assert kb._collection.count() == first


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        'Sure! Here you go:\n{"a": 1}\nHope that helps.',
        '{"a": 1,}',  # trailing comma, handled by json_repair
    ],
)
def test_extract_json_handles_llm_noise(raw):
    assert extract_json(raw) == {"a": 1}


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json("no json here at all")


def test_workflow_runs_once_and_saves_history(client, auth_headers, db_session):
    state = {
        "job": {"id": "1", "title": "Intern", "company": "Acme", "description": "d"},
        "steps": [{"agent": "Orchestrator", "action": "x", "detail": ""}],
    }
    payload = {
        "profile": {"skills": ["Python"]},
        "job_query": "backend intern",
    }
    with patch(
        "app.api.routes_chat.run_full_workflow", new=AsyncMock(return_value=state)
    ) as mock_run:
        r = client.post("/api/workflow/run", json=payload, headers=auth_headers)

    assert r.status_code == 200
    assert mock_run.await_count == 1  # regression test for the double-run bug
    assert db_session.query(UserHistory).count() == 1


def test_upload_too_large_rejected(client, auth_headers):
    big = b"%PDF-" + b"0" * (6 * 1024 * 1024)
    r = client.post(
        "/api/resume/upload",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 413


def test_history_snapshot_upserts_per_job(client, auth_headers, db_session):
    job = {
        "id": "local-1",
        "title": "SWE Intern",
        "company": "Kestrel",
        "description": "d",
    }
    match = {
        "match_score": 80,
        "matched_skills": ["Python"],
        "missing_skills": [],
        "rationale": "ok",
    }

    r1 = client.post("/api/history/snapshot", json={"job": job}, headers=auth_headers)
    r2 = client.post(
        "/api/history/snapshot", json={"job": job, "match": match}, headers=auth_headers
    )
    assert r1.status_code == r2.status_code == 200

    assert db_session.query(UserHistory).count() == 1  # updated, not duplicated
    rows = client.get("/api/history", headers=auth_headers).json()
    assert rows[0]["kind"] == "analysis"
    assert rows[0]["payload"]["match"]["match_score"] == 80
