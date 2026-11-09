"""Admin-only dependency and audit helper."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.admin.models import AuditLog
from app.auth.dependencies import get_current_user
from app.auth.models import User


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required.")
    return user


def audit(
    db: Session, admin: User, action: str, target: str = "", detail: str = ""
) -> None:
    """Write an audit row. Call for every mutation and every read of student data."""
    db.add(
        AuditLog(
            admin_id=admin.id,
            admin_email=admin.email,
            action=action,
            target=str(target),
            detail=detail[:500],
        )
    )
    db.commit()
