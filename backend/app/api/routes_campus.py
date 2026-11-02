from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Query

from app.config import settings

router = APIRouter(prefix="/api/campus", tags=["campus"])


def _load_drives() -> list[dict]:
    path = Path(settings.knowledge_base_dir) / "campus_drives.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _check_eligibility(
    drive: dict, branch: str | None, cgpa: float | None
) -> list[str]:
    """Return the reasons a student is NOT eligible (empty list = eligible)."""
    reasons: list[str] = []
    branches = [b.lower() for b in drive.get("branches", [])]
    if branch and branches and "all" not in branches and branch.lower() not in branches:
        reasons.append(f"Open to {', '.join(drive['branches'])} only")
    min_cgpa = drive.get("min_cgpa")
    if cgpa is not None and min_cgpa is not None and cgpa < min_cgpa:
        reasons.append(f"Needs CGPA ≥ {min_cgpa}")
    return reasons


@router.get("/drives")
async def list_drives(
    job_type: Literal["any", "internship", "full-time"] = "any",
    branch: str | None = Query(default=None, max_length=50),
    cgpa: float | None = Query(default=None, ge=0, le=10),
    location: str | None = Query(default=None, max_length=100),
    include_past: bool = False,
):
    today = datetime.now(UTC).date()
    out = []
    for d in _load_drives():
        drive_date = date.fromisoformat(d["date"])
        if not include_past and drive_date < today:
            continue
        if job_type != "any" and d.get("type") != job_type:
            continue
        if location:
            loc = d.get("location", "").lower()
            if location.lower() not in loc and "remote" not in loc:
                continue
        reasons = _check_eligibility(d, branch, cgpa)
        out.append(
            {
                **d,
                "eligible": not reasons,
                "reasons": reasons,
                "days_left": (drive_date - today).days,
            }
        )
    out.sort(key=lambda d: d["date"])
    return out
