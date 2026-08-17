"""One-off CLI to create the first super_admin account (or any super_admin,
since there's no API route for it — see routers/admin.py).

Usage (from backend/):
    python -m scripts.create_super_admin --username root --password "..." --name "Site Owner"
    python -m scripts.create_super_admin --username root --password "..." --name "Site Owner" --email root@example.com

Idempotent: if the username already exists, it exits without changes
(pass --update to reset that user's password instead).
"""
import argparse
import sys

from sqlalchemy import select

from core.database import SessionLocal
from core.security import hash_password
from models.auth import Profile, Role, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a super_admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True, help="Profile display name")
    parser.add_argument("--email", default=None)
    parser.add_argument("--update", action="store_true", help="If the username exists, reset its password instead of failing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        role = db.execute(select(Role).where(Role.name == "super_admin")).scalar_one_or_none()
        if role is None:
            print("ERROR: 'super_admin' role not found — run `alembic upgrade head` first.", file=sys.stderr)
            sys.exit(1)

        existing = db.execute(select(User).where(User.username == args.username)).scalar_one_or_none()
        if existing is not None:
            if not args.update:
                print(f"ERROR: user '{args.username}' already exists. Pass --update to reset its password.", file=sys.stderr)
                sys.exit(1)
            existing.password_hash = hash_password(args.password)
            existing.is_active = True
            db.commit()
            print(f"Updated password for existing user '{args.username}' (id={existing.id}).")
            return

        profile = Profile(name=args.name)
        db.add(profile)
        db.flush()

        user = User(
            college_id=None,
            profile_id=profile.id,
            role_id=role.id,
            username=args.username,
            email=args.email,
            password_hash=hash_password(args.password),
        )
        db.add(user)
        db.commit()
        print(f"Created super_admin '{args.username}' (id={user.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
