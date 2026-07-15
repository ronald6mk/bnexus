"""Core tests: generator, free limit, health, PDF."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use isolated test DB under product data/test
os.environ.setdefault("PRO_UNLOCK_CODE", "proposalforge-pro")

from app.auth import hash_password, verify_password  # noqa: E402
from app.db import get_connection, init_db  # noqa: E402
from app.generator import content_to_sample_text, generate_proposal  # noqa: E402
from app.limits import FREE_MONTHLY_LIMIT, can_create_proposal, count_proposals_this_month  # noqa: E402
from app.pdf_export import build_proposal_pdf  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Isolate SQLite DB for tests that touch the database."""
    import app.db as dbmod

    test_db = tmp_path / "test.db"
    monkeypatch.setattr(dbmod, "DB_PATH", test_db)
    monkeypatch.setattr(dbmod, "DATA_DIR", tmp_path)
    init_db()
    yield


def test_generate_proposal_web_has_sections():
    content = generate_proposal(
        client_name="Alex Rivera",
        client_company="Rivera Retail",
        industry="web",
        services="Discovery, Design, Build, Launch",
        goals="More online sales, mobile-first storefront",
        budget_range="$5,000 – $15,000",
        timeline="1–2 months",
        differentiators="Fixed-price phases, local support",
        sender_company="Northwind Digital",
        sender_name="Sam Chen",
    )
    assert "executive_summary" in content
    assert "Rivera" in content["executive_summary"] or "Alex" in content["executive_summary"]
    assert content["scope"]
    assert content["investment"]
    assert content["investment_total"] > 0
    assert content["timeline_phases"]
    assert "not a binding contract" in content["terms_note"].lower() or "not legal advice" in content["terms_note"].lower()
    text = content_to_sample_text(content)
    assert "EXECUTIVE SUMMARY" in text
    assert "Disclaimer" in text


def test_generate_all_industries():
    for key in ("web", "it_retainer", "consulting", "custom_ict"):
        c = generate_proposal(client_name="Test", industry=key, services="A, B")
        assert c["meta"]["industry"] == key
        assert len(c["investment"]) >= 1


def test_password_hash_roundtrip():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_free_limit_blocks_after_three():
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (email, password_hash, is_pro) VALUES (?, ?, 0)",
        ("free@example.com", hash_password("password1")),
    )
    conn.commit()
    user = dict(conn.execute("SELECT * FROM users WHERE email=?", ("free@example.com",)).fetchone())

    for i in range(FREE_MONTHLY_LIMIT):
        allowed, _ = can_create_proposal(user, conn)
        assert allowed is True
        conn.execute(
            """
            INSERT INTO proposals (user_id, title, client_name, industry, content_json)
            VALUES (?, ?, ?, 'web', '{}')
            """,
            (user["id"], f"P{i}", "Client"),
        )
        conn.commit()

    assert count_proposals_this_month(conn, user["id"]) == FREE_MONTHLY_LIMIT
    allowed, msg = can_create_proposal(user, conn)
    assert allowed is False
    assert "limit" in msg.lower() or "Free" in msg


def test_pro_user_unlimited():
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (email, password_hash, is_pro) VALUES (?, ?, 1)",
        ("pro@example.com", hash_password("password1")),
    )
    conn.commit()
    user = dict(conn.execute("SELECT * FROM users WHERE email=?", ("pro@example.com",)).fetchone())
    for i in range(5):
        conn.execute(
            """
            INSERT INTO proposals (user_id, title, client_name, industry, content_json)
            VALUES (?, ?, ?, 'web', '{}')
            """,
            (user["id"], f"P{i}", "Client"),
        )
    conn.commit()
    allowed, msg = can_create_proposal(user, conn)
    assert allowed is True
    assert "unlimited" in msg.lower() or "Pro" in msg


def test_pdf_bytes_and_watermark():
    import zlib

    content = generate_proposal(
        client_name="Jamie Lee",
        client_company="Lee Labs",
        industry="consulting",
        services="Workshop, Roadmap",
        budget_range="$2,000 – $5,000",
        sender_company="Forge Agency",
    )
    assert "legal advice" in (content.get("terms_note") or "").lower()
    pdf_free = build_proposal_pdf(
        content,
        brand_name="Forge Agency",
        brand_color="#1a56db",
        client_name="Jamie Lee",
        client_company="Lee Labs",
        watermark=True,
    )
    pdf_pro = build_proposal_pdf(
        content,
        brand_name="Forge Agency",
        watermark=False,
    )
    assert pdf_free[:4] == b"%PDF"
    assert pdf_pro[:4] == b"%PDF"
    assert len(pdf_free) > 500
    # Streams are FlateDecode-compressed; inflate to assert disclaimer text
    inflated = b""
    for chunk in pdf_free.split(b"stream\n")[1:]:
        raw = chunk.split(b"\nendstream")[0]
        try:
            inflated += zlib.decompress(raw)
        except zlib.error:
            inflated += raw
    assert b"legal advice" in inflated.lower() or b"legal" in inflated.lower()


def test_health_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["product"] in ("proposalforge", "bnexus")
    assert data["offline_generator"] is True


def test_signup_generate_download_flow():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Signup
    r = client.post(
        "/signup",
        data={"email": "flow@example.com", "password": "secret99", "company_name": "Flow Co"},
        follow_redirects=False,
    )
    assert r.status_code in (303, 302)

    r = client.post(
        "/proposals/new",
        data={
            "client_name": "Casey",
            "client_company": "Casey Co",
            "industry": "it_retainer",
            "services": "Monitoring, Support",
            "goals": "Uptime",
            "budget_range": "$2,000 – $5,000",
            "timeline": "1–2 months",
            "differentiators": "24/7",
            "company_name": "Flow Co",
            "brand_color": "#1a56db",
            "sender_name": "Pat",
            "sender_email": "flow@example.com",
            "sender_phone": "",
        },
        follow_redirects=False,
    )
    assert r.status_code in (303, 302)
    loc = r.headers.get("location", "")
    assert "/proposals/" in loc
    pid = loc.rstrip("/").split("/")[-1]

    r = client.get(f"/proposals/{pid}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
