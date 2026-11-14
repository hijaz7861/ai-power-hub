"""Promote an existing registered account to administrator.

Run only during an intentional bootstrap window:
BOOTSTRAP_ADMIN_ENABLED=true
BOOTSTRAP_ADMIN_EMAIL=the-existing-account@example.com
python -m backend.scripts.bootstrap_admin

This command never creates a user and exposes no public admin-promotion route.
"""
import os
import sys

from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.models import User


def main() -> int:
    if os.getenv("BOOTSTRAP_ADMIN_ENABLED", "").strip().lower() != "true":
        print("Refusing: set BOOTSTRAP_ADMIN_ENABLED=true for an intentional bootstrap.")
        return 2
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    if not email:
        print("Refusing: BOOTSTRAP_ADMIN_EMAIL is required.")
        return 2

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("No existing account found. Register the account first, then retry.")
            return 1
        if user.role == "admin":
            print("Account is already an administrator.")
            return 0
        user.role = "admin"
        db.commit()
        print(f"Administrator role granted to {email}.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
