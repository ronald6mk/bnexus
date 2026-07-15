"""SQLite database helpers for ProposalForge."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "proposalforge.db"
OPS_DIR = ROOT.parent.parent / "ops"
METRICS_PATH = OPS_DIR / "metrics.json"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "samples").mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    ensure_dirs()
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_pro INTEGER NOT NULL DEFAULT 0,
                company_name TEXT DEFAULT '',
                brand_color TEXT DEFAULT '#1a56db',
                sender_name TEXT DEFAULT '',
                sender_email TEXT DEFAULT '',
                sender_phone TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_company TEXT DEFAULT '',
                industry TEXT NOT NULL DEFAULT 'custom_ict',
                services TEXT DEFAULT '',
                goals TEXT DEFAULT '',
                budget_range TEXT DEFAULT '',
                timeline TEXT DEFAULT '',
                differentiators TEXT DEFAULT '',
                content_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_proposals_user ON proposals(user_id);
            CREATE INDEX IF NOT EXISTS idx_proposals_created ON proposals(created_at);
            """
        )
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return dict(row)
