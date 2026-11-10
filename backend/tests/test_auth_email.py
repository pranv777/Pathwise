import pytest
from fastapi.testclient import TestClient

from app.auth.models import EmailOTP, User
from app.main import app


@pytest.fixture()
def public(db_session, monkeypatch):
    """Unauthenticated client (no get_current_user override) + captured OTPs."""
    from app.auth.db import get_db

    sent = {}
    monkeypatch.setattr(
        "app.api.routes_auth.send_otp_email",
        lambda email, name, otp: sent.__setitem__(email, otp),
    )
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app), sent
    app.dependency_overrides.clear()


SIGNUP = {"name": "Asha", "email": "Asha@Example.com", "password": "s3cretpass"}


def test_signup_needs_the_otp_before_an_account_exists(public, db_session):
    client, sent = public
    assert client.post("/api/auth/register", json=SIGNUP).status_code == 200
    assert db_session.query(User).filter_by(email="asha@example.com").first() is None

    r = client.post(
        "/api/auth/verify-otp",
        json={"email": SIGNUP["email"], "otp": sent["asha@example.com"]},
    )
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "asha@example.com"
    assert "access_token" in r.cookies
    assert client.get("/api/auth/me").json()["name"] == "Asha"
    assert db_session.query(EmailOTP).count() == 0


def test_wrong_code_is_rejected_and_limited(public, db_session):
    client, sent = public
    client.post("/api/auth/register", json=SIGNUP)
    bad = {
        "email": SIGNUP["email"],
        "otp": "000000" if sent["asha@example.com"] != "000000" else "111111",
    }
    for _ in range(5):
        assert client.post("/api/auth/verify-otp", json=bad).status_code == 400
    good = {"email": SIGNUP["email"], "otp": sent["asha@example.com"]}
    assert client.post("/api/auth/verify-otp", json=good).status_code == 429


def test_login_after_signup(public):
    client, sent = public
    client.post("/api/auth/register", json=SIGNUP)
    client.post(
        "/api/auth/verify-otp",
        json={"email": SIGNUP["email"], "otp": sent["asha@example.com"]},
    )
    ok = client.post(
        "/api/auth/login", json={"email": "asha@example.com", "password": "s3cretpass"}
    )
    assert ok.status_code == 200
    bad = client.post(
        "/api/auth/login", json={"email": "asha@example.com", "password": "wrong-pass"}
    )
    assert bad.status_code == 401
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
    )
    assert unknown.status_code == 401


def test_existing_account_cannot_register_again(public):
    client, sent = public
    client.post("/api/auth/register", json=SIGNUP)
    client.post(
        "/api/auth/verify-otp",
        json={"email": SIGNUP["email"], "otp": sent["asha@example.com"]},
    )
    assert client.post("/api/auth/register", json=SIGNUP).status_code == 409


def test_resend_is_rate_limited_per_email(public):
    client, _ = public
    client.post("/api/auth/register", json=SIGNUP)
    assert (
        client.post("/api/auth/resend-otp", json={"email": SIGNUP["email"]}).status_code
        == 429
    )


def test_short_password_is_rejected(public):
    client, _ = public
    assert (
        client.post(
            "/api/auth/register", json={**SIGNUP, "password": "short"}
        ).status_code
        == 422
    )


def _signup(client, sent):
    client.post("/api/auth/register", json=SIGNUP)
    client.post(
        "/api/auth/verify-otp",
        json={"email": SIGNUP["email"], "otp": sent["asha@example.com"]},
    )


def test_forgot_password_does_not_reveal_unknown_emails(public):
    client, sent = public
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert sent == {}


def test_password_reset_flow(public):
    client, sent = public
    _signup(client, sent)
    client.post("/api/auth/forgot-password", json={"email": SIGNUP["email"]})
    r = client.post(
        "/api/auth/reset-password",
        json={
            "email": SIGNUP["email"],
            "otp": sent["asha@example.com"],
            "new_password": "brand-new-pass",
        },
    )
    assert r.status_code == 200
    old = {"email": SIGNUP["email"], "password": SIGNUP["password"]}
    new = {"email": SIGNUP["email"], "password": "brand-new-pass"}
    assert client.post("/api/auth/login", json=old).status_code == 401
    assert client.post("/api/auth/login", json=new).status_code == 200


def test_wrong_reset_code_is_limited(public):
    client, sent = public
    _signup(client, sent)
    client.post("/api/auth/forgot-password", json={"email": SIGNUP["email"]})
    code = sent["asha@example.com"]
    bad = {
        "email": SIGNUP["email"],
        "otp": "000000" if code != "000000" else "111111",
        "new_password": "brand-new-pass",
    }
    for _ in range(5):
        assert client.post("/api/auth/reset-password", json=bad).status_code == 400
    good = {**bad, "otp": code}
    assert client.post("/api/auth/reset-password", json=good).status_code == 429


def test_pending_signup_cannot_be_used_to_reset(public):
    client, sent = public
    client.post("/api/auth/register", json=SIGNUP)  # no account yet
    r = client.post(
        "/api/auth/reset-password",
        json={
            "email": SIGNUP["email"],
            "otp": sent["asha@example.com"],
            "new_password": "brand-new-pass",
        },
    )
    assert r.status_code == 400
