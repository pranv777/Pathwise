from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.agents import memory
from app.auth.models import EmailOTP, SavedJob, User, UserHistory
from app.auth.security import hash_password
from app.rag.vector_store import USER_SCOPED_TYPES

PASSWORD = "s3cretpass"


@pytest.fixture()
def with_password(db_session, test_user):
    test_user.password_hash = hash_password(PASSWORD)
    db_session.commit()
    return test_user


def _delete(client, password):
    return client.request("DELETE", "/api/me", json={"password": password})


def _seed(db, user):
    db.add(UserHistory(user_id=user.id, kind="profile", payload="{}"))
    db.add(
        SavedJob(
            user_id=user.id, job_id="j1", title="Intern", company="Acme", location="",
            description="", url="", source="local", status="saved", notes="",
        )
    )
    db.add(
        EmailOTP(
            email=user.email, name=user.name, password_hash="x", code_hash="y", attempts=0,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            last_sent_at=datetime.now(UTC),
        )
    )
    db.commit()


def test_wrong_password_deletes_nothing(client, db_session, with_password):
    _seed(db_session, with_password)
    with patch("app.api.routes_account.delete_user_documents") as delete_docs:
        r = _delete(client, "wrong-password")
    assert r.status_code == 401
    delete_docs.assert_not_called()
    assert db_session.query(User).filter_by(id=with_password.id).count() == 1
    assert db_session.query(UserHistory).count() == 1


def test_account_without_a_password_cannot_be_deleted_here(client, test_user):
    assert _delete(client, "anything").status_code == 401


def test_admins_cannot_delete_themselves(client, db_session, with_password):
    with_password.is_admin = True
    db_session.commit()
    assert _delete(client, PASSWORD).status_code == 403
    assert db_session.query(User).filter_by(id=with_password.id).count() == 1


def test_delete_account_removes_everything_and_clears_the_cookie(
    client, db_session, with_password, other_user
):
    uid, email = with_password.id, with_password.email
    _seed(db_session, with_password)
    _seed(db_session, other_user)
    memory.add_turn(uid, "s1", "hi", "hello")

    with patch("app.api.routes_account.delete_user_documents") as delete_docs:
        r = _delete(client, PASSWORD)

    assert r.status_code == 204
    assert "access_token" in r.headers.get("set-cookie", "")
    assert db_session.query(User).filter_by(id=uid).count() == 0
    assert db_session.query(UserHistory).filter_by(user_id=uid).count() == 0
    assert db_session.query(SavedJob).filter_by(user_id=uid).count() == 0
    assert db_session.query(EmailOTP).filter_by(email=email).count() == 0
    assert memory.get_messages(uid, "s1") == []
    assert {c.args[1] for c in delete_docs.call_args_list} == USER_SCOPED_TYPES
    assert db_session.query(User).filter_by(id=other_user.id).count() == 1
    assert db_session.query(UserHistory).filter_by(user_id=other_user.id).count() == 1


def test_account_survives_if_vectors_cannot_be_deleted(client, db_session, with_password):
    _seed(db_session, with_password)
    with patch(
        "app.api.routes_account.delete_user_documents", side_effect=RuntimeError("chroma down")
    ):
        with pytest.raises(RuntimeError):
            _delete(client, PASSWORD)
    assert db_session.query(User).filter_by(id=with_password.id).count() == 1
    assert db_session.query(UserHistory).count() == 1
