"""Thin async client that spawns our MCP tool servers over stdio and calls
their tools. Agents import `call_job_search` / `call_github_analysis`
instead of talking to the underlying APIs directly — this keeps the
"agent decides to invoke an external tool via MCP" boundary real rather
than simulated.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPToolError(Exception):
    """Raised when an MCP tool server can't be reached or errors out."""


def _server_params(module: str) -> StdioServerParameters:
    # The MCP SDK only forwards a minimal environment to the child process by
    # default. Pass the full environment so TAVILY_API_KEY / GITHUB_TOKEN set on
    # the host (e.g. Render) reach the tool servers.
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=dict(os.environ),
    )


_JOB_SERVER = _server_params("app.mcp_tools.job_search_server")
_GITHUB_SERVER = _server_params("app.mcp_tools.github_server")

_WINDOWS_HINT = (
    "this is a known Windows event-loop issue; start the API with `python run.py` "
    "instead of `uvicorn --reload`."
)


@asynccontextmanager
async def _session(params: StdioServerParameters):
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


async def call_job_search(query: str, location: str = "", limit: int = 5) -> dict:
    try:
        async with asyncio.timeout(20):
            async with _session(_JOB_SERVER) as session:
                result = await session.call_tool(
                    "search_jobs",
                    {"query": query, "location": location, "limit": limit},
                )
                text = result.content[0].text if result.content else "{}"
                return json.loads(text)
    except TimeoutError:
        raise MCPToolError("Job search tool timed out after 20s.")
    except NotImplementedError as exc:
        raise MCPToolError(
            f"Could not start the job-search MCP server — {_WINDOWS_HINT}"
        ) from exc
    except Exception as exc:
        raise MCPToolError(f"Job search tool failed: {exc}") from exc


async def call_github_analysis(username: str) -> dict:
    try:
        async with asyncio.timeout(15):
            async with _session(_GITHUB_SERVER) as session:
                result = await session.call_tool(
                    "analyze_github_profile", {"username": username}
                )
                text = result.content[0].text if result.content else "{}"
                return json.loads(text)
    except TimeoutError:
        raise MCPToolError("GitHub analysis tool timed out after 15s.")
    except NotImplementedError as exc:
        raise MCPToolError(
            f"Could not start the GitHub MCP server — {_WINDOWS_HINT}"
        ) from exc
    except Exception as exc:
        raise MCPToolError(f"GitHub analysis tool failed: {exc}") from exc
