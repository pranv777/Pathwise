from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.dependencies import get_current_user
from app.auth.models import EmailOTP, User
from app.auth.security import create_access_token, hash_otp, hash_password
from app.main import app

SIGNUP = {"name": "Asha", "email": "asha@example.com", "password": "s3cretpass"}
EMAIL = SIGNUP["email"]


@pytest.fixture()
def public(db_session, monkeypatch):
    from app.auth.db import get_db

    sent = {}
    monkeypatch.setattr(
        "app.api.routes_auth.send_otp_email",
        lambda email, name, otp: sent.__setitem__(email, otp),
    )
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app), sent
    app.dependency_overrides.clear()


def _pending(db, email=EMAIL, code="123456", **overrides):
    row = EmailOTP(
        email=email, name="Asha", password_hash=hash_password("s3cretpass"),
        code_hash=hash_otp(email, code), attempts=0,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        last_sent_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    return row


def test_me_returns_the_current_user(client, test_user):
    body = client.get("/api/auth/me").json()
    assert body["email"] == test_user.email and body["is_admin"] is False


def test_logout_clears_the_cookie(client):
    r = client.post("/api/auth/logout")
    assert r.json() == {"status": "logged out"}
    assert "access_token" in r.headers["set-cookie"]


def test_suspended_accounts_cannot_log_in(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="Asha", password_hash=hash_password("s3cretpass"), status="suspended"))
    db_session.commit()
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "s3cretpass"})
    assert r.status_code == 403


def test_login_records_the_time(public, db_session):
    client, _ = public
    user = User(email=EMAIL, name="Asha", password_hash=hash_password("s3cretpass"))
    db_session.add(user)
    db_session.commit()
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "s3cretpass"})
    assert r.status_code == 200
    db_session.refresh(user)
    assert user.last_login_at is not None


def test_login_with_an_unknown_email_or_wrong_password_is_rejected(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="A", password_hash=hash_password("rightpass")))
    db_session.commit()
    wrong = client.post("/api/auth/login", json={"email": EMAIL, "password": "nope"})
    unknown = client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401


def test_a_failed_email_send_is_a_502_and_leaves_no_cooldown(public, db_session, monkeypatch):
    client, _ = public

    def boom(*_):
        raise RuntimeError("resend down")

    monkeypatch.setattr("app.api.routes_auth.send_otp_email", boom)
    assert client.post("/api/auth/register", json=SIGNUP).status_code == 502
    assert db_session.query(EmailOTP).count() == 0


def test_resend_otp_needs_a_pending_signup(public):
    client, _ = public
    assert client.post("/api/auth/resend-otp", json={"email": EMAIL}).status_code == 404


def test_resend_otp_issues_a_new_code(public, db_session):
    client, sent = public
    _pending(db_session)
    assert client.post("/api/auth/resend-otp", json={"email": EMAIL}).status_code == 200
    assert EMAIL in sent


def test_verify_without_a_pending_signup(public):
    client, _ = public
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": "123456"})
    assert r.status_code == 400


def test_verify_with_an_expired_code(public, db_session):
    client, _ = public
    _pending(db_session, expires_at=datetime.now(UTC) - timedelta(minutes=1))
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": "123456"})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_verify_for_an_email_that_registered_meanwhile(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="A", password_hash=hash_password("x12345678")))
    db_session.commit()
    _pending(db_session)
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": "123456"})
    assert r.status_code == 409
    assert db_session.query(EmailOTP).count() == 0


def test_verify_claims_a_google_only_account(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="Old Name", password_hash=None))
    db_session.commit()
    _pending(db_session)
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": "123456"})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Asha"
    assert db_session.query(User).filter_by(email=EMAIL).one().password_hash


def test_forgot_password_sends_nothing_for_suspended_accounts(public, db_session):
    client, sent = public
    db_session.add(User(email=EMAIL, name="A", password_hash=hash_password("s3cretpass"), status="suspended"))
    db_session.commit()
    assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).json() == {"status": "ok"}
    assert sent == {}


def test_forgot_password_hides_cooldowns(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="A", password_hash=hash_password("s3cretpass")))
    db_session.commit()
    first = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    second = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert first.json() == second.json() == {"status": "ok"}


def test_reset_with_an_expired_code(public, db_session):
    client, _ = public
    db_session.add(User(email=EMAIL, name="A", password_hash=hash_password("oldpass12")))
    db_session.commit()
    _pending(db_session, expires_at=datetime.now(UTC) - timedelta(minutes=1))
    r = client.post(
        "/api/auth/reset-password",
        json={"email": EMAIL, "otp": "123456", "new_password": "brandnewpass"},
    )
    assert r.status_code == 400


def _request(cookie=None):
    headers = [(b"cookie", f"access_token={cookie}".encode())] if cookie else []
    return Request({"type": "http", "headers": headers})


def test_missing_token_is_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request(), None, MagicMock())
    assert exc.value.status_code == 401


def test_garbage_token_is_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request("garbage"), None, MagicMock())
    assert exc.value.status_code == 401


def test_token_for_a_deleted_user_is_401(db_session):
    token = create_access_token(9999, "gone@example.com")
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request(token), None, db_session)
    assert exc.value.status_code == 401


def test_header_token_is_accepted(db_session, test_user):
    token = create_access_token(test_user.id, test_user.email)
    assert get_current_user(_request(), token, db_session).id == test_user.id


def test_cookie_beats_header_and_inactive_users_are_blocked(db_session, test_user):
    token = create_access_token(test_user.id, test_user.email)
    assert get_current_user(_request(token), "ignored", db_session).id == test_user.id
    test_user.status = "suspended"
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request(token), None, db_session)
    assert exc.value.status_code == 403
