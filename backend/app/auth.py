"""Authentication and role-based authorization.

Password hashing uses bcrypt directly (not passlib — passlib 1.7.4's bcrypt
backend detection is broken against bcrypt>=4.0 in this environment, verified
directly; bcrypt's own API is simple enough not to need the wrapper). Tokens are
signed JWTs (HS256) so authorization can be enforced on every protected route
without a server-side session store. Role is always read from the verified
token's claims / the User row in the database — never trusted from a client-
supplied header, query param, or request body field.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.config import Settings, get_settings
from app.db import get_db

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_BCRYPT_MAX_BYTES = 72  # bcrypt's own hard limit; longer inputs are rejected, not silently truncated


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {_BCRYPT_MAX_BYTES} bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user: models.User, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _decode_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials") from None


def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> models.User:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = _decode_token(token, settings)
    user = db.get(models.User, claims.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def seed_demo_users(db: Session, settings: Settings) -> None:
    """Idempotently create the demo accounts listed in settings.demo_users, if they
    don't already exist. Local/demo convenience only — passwords come from
    configuration (see .env.example), never hardcoded in source, and this is a
    no-op once the accounts already exist."""
    spec = settings.demo_users.strip()
    if not spec:
        return
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry:
            continue
        username, password, role = entry.split(":")
        if db.query(models.User).filter_by(username=username).first():
            continue
        db.add(models.User(username=username, password_hash=hash_password(password), role=role))
    db.commit()


def require_roles(*roles: str):
    """Dependency factory: `Depends(require_roles(ROLE_INSPECTOR, ROLE_DEPARTMENT_ADMIN))`.
    Authorization is enforced here, server-side, on every call — never by the
    frontend merely hiding a button."""

    def _check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this action")
        return current_user

    return _check
