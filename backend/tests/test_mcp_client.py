import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.types import TextContent

from app.mcp_tools import mcp_client
from app.mcp_tools.mcp_client import MCPToolError


def _result(*blocks):
    return SimpleNamespace(content=list(blocks))


def _text(payload):
    return TextContent(type="text", text=json.dumps(payload))


class FakeSession:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        if self.exc:
            raise self.exc
        return self.result


def _use(monkeypatch, session):
    @asynccontextmanager
    async def fake(_params):
        yield session

    monkeypatch.setattr(mcp_client, "_session", fake)


def test_job_search_calls_the_tool_and_parses_json(monkeypatch):
    session = FakeSession(_result(_text({"jobs": [1]})))
    _use(monkeypatch, session)
    out = asyncio.run(mcp_client.call_job_search("python", "Pune", 3))
    assert out == {"jobs": [1]}
    assert session.calls == [("search_jobs", {"query": "python", "location": "Pune", "limit": 3})]


def test_github_analysis_calls_the_tool(monkeypatch):
    session = FakeSession(_result(_text({"username": "x"})))
    _use(monkeypatch, session)
    assert asyncio.run(mcp_client.call_github_analysis("x")) == {"username": "x"}
    assert session.calls[0][0] == "analyze_github_profile"


@pytest.mark.parametrize("blocks", [(), (SimpleNamespace(data="img"),)])
def test_non_text_or_empty_results_become_an_empty_dict(monkeypatch, blocks):
    _use(monkeypatch, FakeSession(_result(*blocks)))
    assert asyncio.run(mcp_client.call_job_search("q")) == {}
    assert asyncio.run(mcp_client.call_github_analysis("x")) == {}


@pytest.mark.parametrize(
    "call, args",
    [(mcp_client.call_job_search, ("q",)), (mcp_client.call_github_analysis, ("x",))],
)
@pytest.mark.parametrize(
    "exc, message",
    [
        (RuntimeError("boom"), "failed: boom"),
        (NotImplementedError(), "Windows event-loop"),
        (TimeoutError(), "timed out"),
    ],
)
def test_failures_become_mcp_tool_errors(monkeypatch, call, args, exc, message):
    _use(monkeypatch, FakeSession(exc=exc))
    with pytest.raises(MCPToolError, match=message):
        asyncio.run(call(*args))


def test_server_params_forward_the_environment(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "abc")
    params = mcp_client._server_params("app.mcp_tools.job_search_server")
    assert params.args == ["-m", "app.mcp_tools.job_search_server"]
    assert params.env is not None
    assert params.env["TAVILY_API_KEY"] == "abc"


def test_session_initialises_the_client_session(monkeypatch):
    events = []

    class FakeStdio:
        def __init__(self, params):
            events.append("stdio")

        async def __aenter__(self):
            return ("read", "write")

        async def __aexit__(self, *exc):
            events.append("stdio closed")

    class FakeClient:
        def __init__(self, read, write):
            assert (read, write) == ("read", "write")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            events.append("session closed")

        async def initialize(self):
            events.append("initialize")

    monkeypatch.setattr(mcp_client, "stdio_client", FakeStdio)
    monkeypatch.setattr(mcp_client, "ClientSession", FakeClient)

    async def use():
        async with mcp_client._session(MagicMock()) as session:
            assert isinstance(session, FakeClient)

    asyncio.run(use())
    assert events == ["stdio", "initialize", "session closed", "stdio closed"]
