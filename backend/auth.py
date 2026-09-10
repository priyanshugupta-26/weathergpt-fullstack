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
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
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
    prefs = {}
    if getattr(user, "preferences", None):
        try:
            prefs = json.loads(user.preferences)
        except Exception:
            prefs = {}
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "full_name": user.name,
        "role": user.role,
        "mobile": getattr(user, "mobile", None) or "",
        "preferred_language": getattr(user, "preferred_language", "en") or "en",
        "state": getattr(user, "state", None) or "",
        "district": getattr(user, "district", None) or "",
        "city": getattr(user, "city", None) or "",
        "latitude": getattr(user, "latitude", None),
        "longitude": getattr(user, "longitude", None),
        "is_active": getattr(user, "is_active", 1),
        "created_at": getattr(user, "created_at", None),
        "last_login": getattr(user, "last_login", None),
        "preferences": prefs,
    }
