from unittest.mock import patch

from app.agents import memory
from app.auth.models import SavedJob, UserHistory
from app.rag.vector_store import USER_SCOPED_TYPES


def _seed(db, user):
    db.add(UserHistory(user_id=user.id, kind="profile", payload="{}"))
    db.add(UserHistory(user_id=user.id, kind="analysis", payload="{}"))
    db.add(
        SavedJob(
            user_id=user.id,
            job_id="local-1",
            title="Intern",
            company="Acme",
            location="",
            description="",
            url="",
            source="local",
            status="applied",
            notes="",
        )
    )
    db.commit()


def test_delete_my_data_removes_everything_for_the_user(client, db_session, test_user):
    _seed(db_session, test_user)
    memory.add_turn(test_user.id, "s1", "hi", "hello")

    with patch("app.api.routes_account.delete_user_documents") as delete_docs:
        r = client.delete("/api/me/data")

    assert r.status_code == 204
    assert db_session.query(UserHistory).filter_by(user_id=test_user.id).count() == 0
    assert db_session.query(SavedJob).filter_by(user_id=test_user.id).count() == 0
    assert memory.get_messages(test_user.id, "s1") == []
    assert client.get("/api/profile").json() == {"profile": None}

    # every private document type is wiped from the vector store, for this user only
    assert {c.args[1] for c in delete_docs.call_args_list} == USER_SCOPED_TYPES
    assert all(c.args[0] == test_user.id for c in delete_docs.call_args_list)


def test_delete_my_data_leaves_other_users_alone(
    client, db_session, test_user, other_user
):
    _seed(db_session, test_user)
    _seed(db_session, other_user)

    with patch("app.api.routes_account.delete_user_documents"):
        client.delete("/api/me/data")

    assert db_session.query(UserHistory).filter_by(user_id=other_user.id).count() == 2
    assert db_session.query(SavedJob).filter_by(user_id=other_user.id).count() == 1


def test_delete_keeps_the_account(client, db_session, test_user):
    with patch("app.api.routes_account.delete_user_documents"):
        client.delete("/api/me/data")
    assert client.get("/api/auth/me").status_code == 200


def test_vector_store_failure_does_not_delete_database_rows(
    client, db_session, test_user
):
    _seed(db_session, test_user)

    with patch(
        "app.api.routes_account.delete_user_documents",
        side_effect=RuntimeError("chroma down"),
    ):
        try:
            client.delete("/api/me/data")
        except RuntimeError:
            pass  # TestClient re-raises unhandled server errors

    # vectors are deleted first, so a failure leaves everything intact for a retry
    assert db_session.query(UserHistory).filter_by(user_id=test_user.id).count() == 2
    assert db_session.query(SavedJob).filter_by(user_id=test_user.id).count() == 1


def test_delete_my_data_requires_login():
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).delete("/api/me/data").status_code == 401
