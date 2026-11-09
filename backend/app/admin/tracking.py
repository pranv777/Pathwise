"""Record agent runs and MCP calls without ever breaking the real request.

    @track("resume")                 # works on sync and async functions
    def run_resume_agent(...): ...

Only the agent name, outcome, duration and the *exception class* are stored.
Exception messages are dropped on purpose: pydantic validation errors echo the
offending input, which for the resume agent is the student's resume.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.admin.models import AgentRun
from app.auth.db import SessionLocal

logger = logging.getLogger("admin.tracking")
F = TypeVar("F", bound=Callable[..., Any])


def _record(kind: str, name: str, started: float, error: str) -> None:
    # Unit tests exercise the real agents with mocked LLMs; don't write to the
    # developer's database from them. tests/test_admin.py clears this variable.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        with SessionLocal() as db:
            db.add(
                AgentRun(
                    kind=kind,
                    name=name,
                    status="failed" if error else "success",
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                    error=error,
                )
            )
            db.commit()
    except Exception:
        logger.warning("could not record %s run %s", kind, name, exc_info=True)


def _payload_error(result: Any) -> str:
    """MCP tools report some failures inside the returned dict."""
    if isinstance(result, dict) and result.get("error"):
        return "ToolReportedError"
    return ""


def track(name: str, kind: str = "agent") -> Callable[[F], F]:
    def deco(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def awrapper(*args: Any, **kwargs: Any) -> Any:
                started = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                except BaseException as exc:
                    await asyncio.to_thread(
                        _record, kind, name, started, type(exc).__name__
                    )
                    raise
                err = _payload_error(result) if kind == "mcp" else ""
                await asyncio.to_thread(_record, kind, name, started, err)
                return result

            return awrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except BaseException as exc:
                _record(kind, name, started, type(exc).__name__)
                raise
            _record(kind, name, started, "")
            return result

        return wrapper  # type: ignore[return-value]

    return deco


def track_agent(name: str) -> Callable[[F], F]:
    return track(name, "agent")


def track_mcp(name: str) -> Callable[[F], F]:
    return track(name, "mcp")
