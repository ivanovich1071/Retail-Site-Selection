"""Reset passwords for existing users (and create the default account if absent).

Usage:
    python scripts/reset_passwords.py                 # reset ALL users to DEFAULT_PASSWORD
    python scripts/reset_passwords.py user@mail.ru    # reset/create just this user

Sets a known password so you can log in again, then change it later.
"""
import asyncio
import sys

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.api.v1.endpoints.auth import hash_password

DEFAULT_PASSWORD = "Evrotorg2026!"
DEFAULT_EMAIL = "pts.bryansk@mail.ru"


async def reset(target_email: str | None) -> None:
    async with AsyncSessionLocal() as db:
        if target_email:
            result = await db.execute(select(User).where(User.email == target_email))
            user = result.scalar_one_or_none()
            if user:
                user.hashed_password = hash_password(DEFAULT_PASSWORD)
                print(f"reset password: {target_email}")
            else:
                db.add(User(
                    email=target_email,
                    hashed_password=hash_password(DEFAULT_PASSWORD),
                    full_name="PTS Bryansk",
                ))
                print(f"created user: {target_email}")
        else:
            users = (await db.execute(select(User))).scalars().all()
            if not users:
                db.add(User(
                    email=DEFAULT_EMAIL,
                    hashed_password=hash_password(DEFAULT_PASSWORD),
                    full_name="PTS Bryansk",
                ))
                print(f"no users found — created default: {DEFAULT_EMAIL}")
            for u in users:
                u.hashed_password = hash_password(DEFAULT_PASSWORD)
                print(f"reset password: {u.email}")

        await db.commit()
    print(f"\nPassword set to: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(reset(arg))
