"""Simple session-cookie authentication (stdlib hashlib + secrets)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Optional

from fastapi import Request, Response

# In-memory session store: token -> {user_id, email, exp}
# Note: free-tier restarts clear sessions (re-login). Secret used for cookie bind.
_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_COOKIE = "pf_session"
SESSION_DAYS = 14
_PBKDF2_ITERATIONS = 120_000


def _app_secret() -> str:
    """Matches main.app_secret aliases (Render may use PROPOSALFORGESECRET)."""
    for key in ("PROPOSALFORGE_SECRET", "PROPOSALFORGESECRET", "BNEXUS_SECRET"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return "dev-insecure-change-me"


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
    raw = secrets.token_urlsafe(32)
    # Bind token to registered secret so env typo vs underscore still works if rotated carefully
    sig = hmac.new(
        _app_secret().encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]
    token = f"{raw}.{sig}"
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
    # Validate secret-bound signature when present
    if "." in token:
        raw, sig = token.rsplit(".", 1)
        expect = hmac.new(
            _app_secret().encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:16]
        if not hmac.compare_digest(sig, expect):
            return None
    data = _SESSIONS.get(token)
    if not data:
        return None
    if data["exp"] < time.time():
        del _SESSIONS[token]
        return None
    return data


def set_session_cookie(response: Response, token: str) -> None:
    # secure=True only in production HTTPS (Render). Off for local/pytest.
    use_secure = os.environ.get("RENDER", "").lower() in ("true", "1") or bool(
        os.environ.get("RENDER_EXTERNAL_URL")
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=use_secure,
        max_age=SESSION_DAYS * 86400,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def session_from_request(request: Request) -> Optional[dict[str, Any]]:
    return get_session(request.cookies.get(SESSION_COOKIE))
