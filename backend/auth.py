import hashlib
import time
from argon2 import PasswordHasher
from fastapi import HTTPException, Request
from .database import Session, User, AuthSession

hasher = PasswordHasher()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def optional_user(request: Request):
    token = request.cookies.get("wg_session")
    if not token:
        return None
    with Session() as db:
        session = db.get(AuthSession, token_hash(token))
        if session and session.expires > time.time():
            return db.get(User, session.user_id)
    return None


def require_user(request: Request):
    user = optional_user(request)
    if user is None:
        raise HTTPException(401, "Sign in to continue")
    return user


def require_admin(request: Request):
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def public_user(user):
    import json

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "preferences": json.loads(user.preferences),
    }
