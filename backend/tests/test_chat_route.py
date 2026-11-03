from unittest.mock import AsyncMock, patch

from app.models.schemas import AgentStep


def test_chat_returns_the_reply_and_agent_steps(client, test_user):
    steps = [
        AgentStep(agent="Orchestrator", action="Routed to: rag_answer", detail="x")
    ]
    with patch(
        "app.api.routes_chat.run_chat_orchestrator",
        new=AsyncMock(return_value=("hello there", steps)),
    ) as orchestrator:
        r = client.post("/api/chat", json={"message": "hi", "session_id": "abc"})

    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "hello there"
    assert body["steps"][0]["agent"] == "Orchestrator"

    message, profile, user_id, session_id = orchestrator.await_args.args
    assert message == "hi"
    assert profile is None
    assert user_id == test_user.id
    assert session_id == "abc"


def test_chat_passes_the_profile_through(client):
    with patch(
        "app.api.routes_chat.run_chat_orchestrator",
        new=AsyncMock(return_value=("ok", [])),
    ) as orchestrator:
        client.post(
            "/api/chat",
            json={"message": "hi", "profile": {"name": "Asha", "skills": ["Python"]}},
        )

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
