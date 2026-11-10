from unittest.mock import AsyncMock, patch


def test_chat_returns_the_reply(client, test_user):
    with patch(
        "app.api.routes_chat.run_chat_orchestrator",
        new=AsyncMock(return_value="hello there"),
    ) as orchestrator:
        r = client.post("/api/chat", json={"message": "hi", "session_id": "abc"})

    assert r.status_code == 200
    assert r.json() == {"reply": "hello there"}

    assert orchestrator.await_args is not None
    message, profile, user_id, session_id = orchestrator.await_args.args
    assert message == "hi"
    assert profile is None
    assert user_id == test_user.id
    assert session_id == "abc"


def test_chat_passes_the_profile_through(client):
    with patch(
        "app.api.routes_chat.run_chat_orchestrator", new=AsyncMock(return_value="ok")
    ) as orchestrator:
        client.post(
            "/api/chat",
            json={"message": "hi", "profile": {"name": "Asha", "skills": ["Python"]}},
        )

    assert orchestrator.await_args is not None
    profile = orchestrator.await_args.args[1]
    assert profile.name == "Asha"
    assert profile.skills == ["Python"]


def test_chat_failure_becomes_a_502(client):
    with patch(
        "app.api.routes_chat.run_chat_orchestrator",
        new=AsyncMock(side_effect=RuntimeError("LLM down")),
    ):
        r = client.post("/api/chat", json={"message": "hi"})

    assert r.status_code == 502
    assert "Assistant failed" in r.json()["detail"]


def test_chat_rejects_empty_and_oversized_messages(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 2001}).status_code == 422
