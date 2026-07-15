"""Simple JSON metrics for ops/metrics.json."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db import METRICS_PATH, OPS_DIR

_lock = threading.Lock()


def _default_metrics() -> dict[str, Any]:
    return {
        "product": "proposalforge",
        "proposals_generated": 0,
        "pdfs_downloaded": 0,
        "signups": 0,
        "dfy_orders": 0,
        "logins": 0,
        "last_events": [],
        "updated_at": None,
    }


def load_metrics() -> dict[str, Any]:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    if not METRICS_PATH.exists():
        data = _default_metrics()
        save_metrics(data)
        return data
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        base = _default_metrics()
        base.update(data)
        return base
    except (json.JSONDecodeError, OSError):
        return _default_metrics()


def save_metrics(data: dict[str, Any]) -> None:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def track(event: str, **extra: Any) -> None:
    with _lock:
        data = load_metrics()
        if event == "generate":
            data["proposals_generated"] = int(data.get("proposals_generated", 0)) + 1
        elif event == "download":
            data["pdfs_downloaded"] = int(data.get("pdfs_downloaded", 0)) + 1
        elif event == "signup":
            data["signups"] = int(data.get("signups", 0)) + 1
        elif event == "dfy":
            data["dfy_orders"] = int(data.get("dfy_orders", 0)) + 1
        elif event == "login":
            data["logins"] = int(data.get("logins", 0)) + 1

        events = list(data.get("last_events") or [])
        events.insert(
            0,
            {
                "event": event,
                "at": datetime.now(timezone.utc).isoformat(),
                **{k: v for k, v in extra.items() if v is not None},
            },
        )
        data["last_events"] = events[:50]
        save_metrics(data)
