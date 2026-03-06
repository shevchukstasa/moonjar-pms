"""
Seed the first owner user.
Usage: python -m scripts.seed_owner --email admin@moonjar.com --password admin123
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.auth import hash_password
from api.models import User


def main():
    parser = argparse.ArgumentParser(description="Create the first owner user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Owner")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            print(f"User {args.email} already exists.")
            return

        user = User(
            email=args.email,
            name=args.name,
            role="owner",
            password_hash=hash_password(args.password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Owner user created: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
