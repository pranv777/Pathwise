"""Admin API, mounted under /api/admin and gated by require_admin.

Privacy: agent/MCP logs hold metadata only. Student detail returns skills and
history *kinds and timestamps*, never raw resume text, and every view is
written to the audit log.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import threading
from datetime import UTC, datetime, timedelta
from datetime import date as Date
from pathlib import Path
from typing import Any, Literal

from chromadb.api.types import IncludeEnum
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.admin.deps import audit, require_admin
from app.admin.models import AgentRun, AuditLog
from app.agents.memory import clear_user
from app.auth.db import get_db
from app.auth.models import SavedJob, User, UserHistory
from app.config import settings
from app.rag.vector_store import USER_SCOPED_TYPES, delete_user_documents

router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

AGENTS = [
    "resume",
    "job_matching",
    "skill_gap",
    "learning",
    "interview",
    "orchestrator",
]
MCP_SERVERS = [
    {"id": "job_search", "name": "Job Search", "tools": ["search_jobs"]},
    {"id": "github", "name": "GitHub Analysis", "tools": ["analyze_github_profile"]},
]
Status = Literal["active", "suspended", "deactivated"]


def _now() -> datetime:
    return datetime.now(UTC)


def _failed_sum():
    return func.sum(case((AgentRun.status == "failed", 1), else_=0))


# ───────────────────────── Overview ─────────────────────────
@router.get("/overview")
def overview(days: int = Query(14, ge=7, le=90), db: Session = Depends(get_db)):
    now = _now()
    since = now - timedelta(days=days)
    students = User.is_admin.is_(False)

    def count(*where) -> int:
        return db.scalar(select(func.count()).where(*where)) or 0

    runs_total = count(AgentRun.kind == "agent")
    runs_failed = count(AgentRun.kind == "agent", AgentRun.status == "failed")
    today = now.date().isoformat()
    active_drives = sum(1 for d in _read_drives() if str(d.get("date", "")) >= today)

    def per_day(col, *filters):
        rows = db.execute(
            select(func.date(col), func.count())
            .where(col >= since, *filters)
            .group_by(func.date(col))
        ).all()
        found = {str(d): n for d, n in rows}
        days_list = [
            (since + timedelta(days=i + 1)).date().isoformat() for i in range(days)
        ]
        return [{"date": d, "count": found.get(d, 0)} for d in days_list]

    usage = db.execute(
        select(AgentRun.name, func.count())
        .where(AgentRun.kind == "agent")
        .group_by(AgentRun.name)
        .order_by(func.count().desc())
    ).all()
    pipeline: dict[str, int] = {
        s: n
        for s, n in db.execute(
            select(SavedJob.status, func.count()).group_by(SavedJob.status)
        ).all()
    }

    return {
        "stats": {
            "students": count(User.id.is_not(None), students),
            "active_students": count(
                students, User.last_login_at >= now - timedelta(days=30)
            ),
            "resumes": count(UserHistory.kind == "profile"),
            "saved_jobs": count(SavedJob.id.is_not(None)),
            "active_drives": active_drives,
            "ai_interactions": runs_total,
            "agent_failures": runs_failed,
            "agent_success_rate": round(
                100 * (runs_total - runs_failed) / runs_total, 1
            )
            if runs_total
            else None,
        },
        "registrations": per_day(User.created_at, students),
        "activity": per_day(AgentRun.created_at, AgentRun.kind == "agent"),
        "agent_usage": [{"name": n, "count": c} for n, c in usage],
        "placement_pipeline": [
            {"status": s, "count": pipeline.get(s, 0)}
            for s in ["saved", "applied", "interview", "offer", "rejected"]
        ],
    }


# ───────────────────────── Students ─────────────────────────
def _student_row(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "status": u.status,
        "created_at": u.created_at,
        "last_login_at": u.last_login_at,
    }


def _student_query(q: str | None, status_: str | None):
    stmt = select(User).where(User.is_admin.is_(False))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.name.ilike(like)))
    if status_:
        stmt = stmt.where(User.status == status_)
    return stmt


@router.get("/students")
def list_students(
    q: str | None = Query(None, max_length=100),
    status: Status | None = None,
    since: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = _student_query(q, status)
    if since:
        stmt = stmt.where(User.created_at >= since)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"total": total, "page": page, "items": [_student_row(u) for u in rows]}


def _csv_safe(v) -> str:
    """Neutralise spreadsheet formula injection (names are user-controlled)."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@router.get("/students/export.csv")
def export_students(
    q: str | None = Query(None, max_length=100),
    status: Status | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(_student_query(q, status).order_by(User.id)).all()
    cols = ["id", "email", "name", "status", "created_at", "last_login_at"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for u in rows:
        r = _student_row(u)
        w.writerow([_csv_safe(r[c]) for c in cols])
    audit(db, admin, "students.export", detail=f"{len(rows)} rows")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="students.csv"'},
    )


def _get_student(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if not u or u.is_admin:
        raise HTTPException(404, "Student not found.")
    return u


@router.get("/students/{user_id}")
def student_detail(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    u = _get_student(db, user_id)
    skills: list[str] = []
    profile = db.scalar(
        select(UserHistory).where(
            UserHistory.user_id == u.id, UserHistory.kind == "profile"
        )
    )
    if profile:
        try:
            skills = [str(s) for s in json.loads(profile.payload).get("skills", [])][
                :100
            ]
        except (ValueError, AttributeError):
            skills = []
    history = db.scalars(
        select(UserHistory)
        .where(UserHistory.user_id == u.id)
        .order_by(UserHistory.id.desc())
        .limit(100)
    ).all()
    saved = db.scalars(select(SavedJob).where(SavedJob.user_id == u.id)).all()
    audit(db, admin, "student.view", target=f"user:{u.id}")
    return {
        **_student_row(u),
        "skills": skills,
        # kind + timestamp only: the payloads contain resume-derived content.
        "activity": [{"id": h.id, "kind": h.kind, "at": h.created_at} for h in history],
        "saved_jobs": [
            {"id": s.id, "title": s.title, "company": s.company, "status": s.status}
            for s in saved
        ],
    }


class StatusBody(BaseModel):
    status: Status


@router.patch("/students/{user_id}/status")
def set_status(
    user_id: int,
    body: StatusBody,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = _get_student(db, user_id)
    u.status = body.status
    db.commit()
    audit(db, admin, "student.status", target=f"user:{u.id}", detail=body.status)
    return _student_row(u)


@router.delete("/students/{user_id}", status_code=204)
def delete_student(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    u = _get_student(db, user_id)
    # Vectors first: if this fails nothing is deleted and the admin can retry
    # (same order as DELETE /api/me/data).
    try:
        for doc_type in sorted(USER_SCOPED_TYPES):
            delete_user_documents(u.id, doc_type)
    except Exception as exc:
        raise HTTPException(
            502,
            f"Could not remove the student's indexed documents: {type(exc).__name__}",
        ) from exc
    db.query(SavedJob).filter(SavedJob.user_id == u.id).delete(
        synchronize_session=False
    )
    db.query(UserHistory).filter(UserHistory.user_id == u.id).delete(
        synchronize_session=False
    )
    db.delete(u)
    db.commit()
    clear_user(user_id)
    audit(db, admin, "student.delete", target=f"user:{user_id}")


# ───────────────────────── Campus drives ─────────────────────────
# Same file and schema that GET /api/campus/drives reads, so drives created
# here appear to students immediately.
_drives_lock = threading.Lock()


def _drives_path() -> Path:
    return Path(settings.knowledge_base_dir) / "campus_drives.json"


class DriveIn(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    type: Literal["internship", "full-time"] = "full-time"
    date: Date
    apply_by: Date | None = None
    location: str = Field(default="", max_length=120)
    branches: list[str] = Field(default_factory=list, max_length=20)
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    pay: str = Field(default="", max_length=80)
    url: str = Field(default="", max_length=500, pattern=r"^(https?://.*)?$")
    description: str = Field(default="", max_length=2000)


def _read_drives() -> list[dict]:
    path = _drives_path()
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _write_drives(items: list[dict]) -> None:
    path = _drives_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)  # atomic: a crash never leaves a half-written file


def _drive_dict(body: DriveIn) -> dict:
    d = body.model_dump(mode="json")
    if d["apply_by"] is None:
        d.pop("apply_by")
    return d


@router.get("/drives")
def list_drives():
    return sorted(_read_drives(), key=lambda d: d.get("date", ""))


@router.post("/drives", status_code=201)
def create_drive(
    body: DriveIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    with _drives_lock:
        items = _read_drives()
        nums = [
            int(str(d["id"]).removeprefix("drive-"))
            for d in items
            if str(d.get("id", "")).removeprefix("drive-").isdigit()
        ]
        item = {"id": f"drive-{max(nums, default=0) + 1}", **_drive_dict(body)}
        items.append(item)
        _write_drives(items)
    audit(db, admin, "drive.create", target=item["id"], detail=body.company)
    return item


@router.put("/drives/{drive_id}")
def update_drive(
    drive_id: str,
    body: DriveIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    with _drives_lock:
        items = _read_drives()
        for i, d in enumerate(items):
            if str(d.get("id")) == drive_id:
                items[i] = {"id": d["id"], **_drive_dict(body)}
                _write_drives(items)
                break
        else:
            raise HTTPException(404, "Drive not found.")
    audit(db, admin, "drive.update", target=drive_id, detail=body.company)
    return items[i]


@router.delete("/drives/{drive_id}", status_code=204)
def delete_drive(
    drive_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    with _drives_lock:
        items = _read_drives()
        kept = [d for d in items if str(d.get("id")) != drive_id]
        if len(kept) == len(items):
            raise HTTPException(404, "Drive not found.")
        _write_drives(kept)
    audit(db, admin, "drive.delete", target=drive_id)


# ───────────────────────── Agents ─────────────────────────
@router.get("/agents")
def agents_summary(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            AgentRun.name,
            func.count(),
            _failed_sum(),
            func.avg(AgentRun.duration_ms),
            func.max(AgentRun.created_at),
        )
        .where(AgentRun.kind == "agent")
        .group_by(AgentRun.name)
    ).all()
    by = {r[0]: r for r in rows}
    out = []
    for name in AGENTS:
        r = by.get(name)
        total = r[1] if r else 0
        failed = int(r[2] or 0) if r else 0
        out.append(
            {
                "name": name,
                "runs": total,
                "failed": failed,
                "success_rate": round(100 * (total - failed) / total, 1)
                if total
                else None,
                "avg_ms": round(r[3]) if r and r[3] else None,
                "last_run": r[4] if r else None,
            }
        )
    return out


@router.get("/runs")
def list_runs(
    kind: Literal["agent", "mcp"] = "agent",
    name: str | None = Query(None, max_length=60),
    status: Literal["success", "failed"] | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(AgentRun).where(AgentRun.kind == kind)
    if name:
        stmt = stmt.where(AgentRun.name == name)
    if status:
        stmt = stmt.where(AgentRun.status == status)
    rows = db.scalars(stmt.order_by(AgentRun.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "error": r.error,
            "at": r.created_at,
        }
        for r in rows
    ]


# ───────────────────────── Knowledge base ─────────────────────────
SHARED_TYPES = {
    "career_guide",
    "interview_prep",
    "learning_resource",
    "job_description",
}
UPLOAD_EXT = {"pdf", "docx", "txt", "md"}
MAX_UPLOAD = settings.max_upload_mb * 1024 * 1024


def _collection():
    from app.rag.vector_store import get_store

    return get_store()._collection


def _shared_only(**extra) -> dict:
    """Chroma filter that can never match a student's private documents."""
    cond = [{"doc_type": {"$nin": sorted(USER_SCOPED_TYPES)}}]
    cond += [{k: v} for k, v in extra.items()]
    return cond[0] if len(cond) == 1 else {"$and": cond}


@router.get("/kb")
def kb_list() -> dict[str, Any]:
    try:
        data = _collection().get(where=_shared_only(), include=[IncludeEnum.metadatas])
    except Exception as exc:
        raise HTTPException(
            503, f"Vector store unavailable: {type(exc).__name__}"
        ) from exc
    # ...rest of the function unchanged
    docs: dict[str, dict] = {}
    for m in data.get("metadatas") or []:
        m = m or {}
        key = str(m.get("source") or "unknown")
        d = docs.setdefault(
            key, {"source": key, "doc_type": m.get("doc_type", ""), "chunks": 0}
        )
        d["chunks"] += 1
    items = sorted(docs.values(), key=lambda d: d["source"])
    return {
        "documents": len(items),
        "chunks": sum(d["chunks"] for d in items),
        "items": items,
    }


@router.post("/kb", status_code=201)
async def kb_upload(
    doc_type: str = Query(...),
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.rag.vector_store import add_document
    from app.utils.text_extraction import extract_text

    if doc_type not in SHARED_TYPES:
        raise HTTPException(400, "Invalid document type.")
    name = Path(file.filename or "").name
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if ext not in UPLOAD_EXT:
        raise HTTPException(400, "Supported types: PDF, DOCX, TXT, MD.")
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, f"File too large (max {settings.max_upload_mb} MB).")
    try:
        text = await asyncio.to_thread(
            extract_text, "doc.txt" if ext == "md" else name, raw
        )
    except Exception as exc:
        raise HTTPException(422, f"Could not read this file: {exc}") from exc
    if not text.strip():
        raise HTTPException(422, "Could not extract any text from this file.")
    try:
        # Replace-on-reupload, scoped so a student's resume that happens to share
        # the filename is never touched.
        await asyncio.to_thread(_collection().delete, where=_shared_only(source=name))
        chunks = await asyncio.to_thread(
            add_document, text, name, doc_type, None, 1200, 150, True
        )
    except Exception as exc:
        raise HTTPException(502, f"Indexing failed: {type(exc).__name__}") from exc
    audit(db, admin, "kb.upload", target=name, detail=doc_type)
    return {"source": name, "doc_type": doc_type, "chunks": chunks}


@router.delete("/kb", status_code=204)
def kb_delete(
    source: str = Query(..., max_length=300),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        _collection().delete(where=_shared_only(source=source))
    except Exception as exc:
        raise HTTPException(
            503, f"Vector store unavailable: {type(exc).__name__}"
        ) from exc
    audit(db, admin, "kb.delete", target=source)


@router.post("/kb/reseed")
def kb_reseed(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from app.rag.ingest import ingest_seed_kb

    try:
        result = ingest_seed_kb()
    except Exception as exc:
        raise HTTPException(502, f"Seeding failed: {type(exc).__name__}") from exc
    audit(db, admin, "kb.reseed")
    return result


# ───────────────────────── MCP ─────────────────────────
@router.get("/mcp")
def mcp_status(db: Session = Depends(get_db)):
    since = _now() - timedelta(days=7)
    out = []
    for s in MCP_SERVERS:
        tools = []
        for t in s["tools"]:
            total, failed, avg, last_id = db.execute(
                select(
                    func.count(),
                    _failed_sum(),
                    func.avg(AgentRun.duration_ms),
                    func.max(AgentRun.id),
                ).where(
                    AgentRun.kind == "mcp",
                    AgentRun.name == t,
                    AgentRun.created_at >= since,
                )
            ).one()
            last = db.get(AgentRun, last_id) if last_id else None
            tools.append(
                {
                    "name": t,
                    "calls_7d": total,
                    "failed_7d": int(failed or 0),
                    "avg_ms": round(avg) if avg else None,
                    "last_status": last.status if last else None,
                }
            )
        # Health is inferred from the latest call; we never spawn a server to ping it.
        statuses = [t["last_status"] for t in tools if t["last_status"]]
        health = (
            "unknown"
            if not statuses
            else "degraded"
            if "failed" in statuses
            else "healthy"
        )
        out.append({"id": s["id"], "name": s["name"], "health": health, "tools": tools})
    return out


# ───────────────────────── Audit log ─────────────────────────
@router.get("/audit")
def audit_log(
    action: str | None = Query(None, max_length=60),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "admin": r.admin_email,
            "action": r.action,
            "target": r.target,
            "detail": r.detail,
            "at": r.created_at,
        }
        for r in rows
    ]
