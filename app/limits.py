"""Free-tier monthly proposal limits."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

FREE_MONTHLY_LIMIT = 3


def _calendar_month_bounds() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def count_proposals_this_month(conn: sqlite3.Connection, user_id: int) -> int:
    start, end = _calendar_month_bounds()
    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM proposals
        WHERE user_id = ? AND created_at >= ? AND created_at < ?
        """,
        (user_id, start, end),
    ).fetchone()
    return int(row["c"] if row else 0)


def can_create_proposal(user: dict[str, Any], conn: sqlite3.Connection) -> tuple[bool, str]:
    """Return (allowed, message). Pro users always allowed."""
    if user.get("is_pro"):
        return True, "Pro — unlimited"
    used = count_proposals_this_month(conn, int(user["id"]))
    if used >= FREE_MONTHLY_LIMIT:
        return (
            False,
            f"Free tier limit reached ({FREE_MONTHLY_LIMIT}/month). Upgrade to Pro for unlimited proposals.",
        )
    remaining = FREE_MONTHLY_LIMIT - used
    return True, f"Free tier: {remaining} of {FREE_MONTHLY_LIMIT} remaining this month"


def usage_summary(user: dict[str, Any], conn: sqlite3.Connection) -> dict[str, Any]:
    used = count_proposals_this_month(conn, int(user["id"]))
    is_pro = bool(user.get("is_pro"))
    return {
        "is_pro": is_pro,
        "used_this_month": used,
        "limit": None if is_pro else FREE_MONTHLY_LIMIT,
        "remaining": None if is_pro else max(0, FREE_MONTHLY_LIMIT - used),
    }
