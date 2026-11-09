"""Tables used only by the admin module.

Import this module in alembic/env.py (see PATCHES.md) so migrations see it.
Nothing here stores resume text or other personal content on purpose.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AgentRun(Base):
    """One execution of an agent (kind="agent") or an MCP tool call (kind="mcp")."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String, index=True)  # "agent" | "mcp"
    name: Mapped[str] = mapped_column(
        String, index=True
    )  # "resume", "search_jobs", ...
    status: Mapped[str] = mapped_column(String, index=True)  # "success" | "failed"
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    # Exception type + a truncated message. Never prompt or resume content.
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class AuditLog(Base):
    """Who did what in the admin area, including reads of student data."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    admin_email: Mapped[str] = mapped_column(String, default="")
    action: Mapped[str] = mapped_column(String, index=True)  # "student.view", ...
    target: Mapped[str] = mapped_column(String, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
