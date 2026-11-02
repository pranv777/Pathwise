from app.auth.security import create_access_token, decode_access_token


def test_token_roundtrip(test_user):
    token = create_access_token(test_user.id, test_user.email)
    payload = decode_access_token(token)
    assert payload["sub"] == str(test_user.id)
    assert payload["email"] == test_user.email


def test_invalid_token_raises():
    import pytest

    with pytest.raises(ValueError):
        decode_access_token("not.a.real.token")


def test_protected_route_without_token_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post("/api/resume/upload")
    assert r.status_code == 401


def test_protected_route_with_valid_token(client, auth_headers, test_user):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == test_user.email
