"""Simple session-cookie authentication (stdlib hashlib + secrets)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any, Optional

from fastapi import Request, Response

# In-memory session store: token -> {user_id, email, exp}
_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_COOKIE = "pf_session"
SESSION_DAYS = 14
_PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iters,
        )
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, TypeError):
        return False


def create_session(user_id: int, email: str) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "user_id": user_id,
        "email": email,
        "exp": time.time() + SESSION_DAYS * 86400,
    }
    return token


def destroy_session(token: Optional[str]) -> None:
    if token and token in _SESSIONS:
        del _SESSIONS[token]


def get_session(token: Optional[str]) -> Optional[dict[str, Any]]:
    if not token:
        return None
    data = _SESSIONS.get(token)
    if not data:
        return None
    if data["exp"] < time.time():
        del _SESSIONS[token]
        return None
    return data


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_DAYS * 86400,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def session_from_request(request: Request) -> Optional[dict[str, Any]]:
    return get_session(request.cookies.get(SESSION_COOKIE))
