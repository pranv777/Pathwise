"""Promote an existing account to admin:  python -m scripts.make_admin you@college.edu

There is deliberately no HTTP endpoint for this, so the first admin can only be
created by someone with shell access to the server.
"""

import sys

from sqlalchemy import select

from app.auth.db import SessionLocal
from app.auth.models import User


def main(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower().strip()))
        if not user:
            sys.exit(f"No user with email {email}")
        user.is_admin = True
        user.status = "active"
        db.commit()
        print(f"{user.email} is now an admin")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.make_admin <email>")
    main(sys.argv[1])
