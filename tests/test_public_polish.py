"""Guardrails: no technical leakage on public HTML; status is human page."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FORBIDDEN = [
    r"sqlite",
    r"is_pro\s*=",
    r"ADMIN_PRO_EMAIL",
    r"PAYMENT_LINK_",
    r"PROPOSALFORGE",
    r"secret_env",
    r"data/dfy_orders",
    r"proposalforge-pro",
    r"Traceback",
]


def test_api_health_is_minimal():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "secret" not in str(data).lower()
    assert "PROPOSALFORGE" not in str(data)


def test_status_page_is_html_not_json():
    r = client.get("/status")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "All systems operational" in r.text
    assert "secret_env" not in r.text


def test_public_pages_have_no_dev_jargon():
    for path in ("/", "/dfy", "/samples", "/status", "/signup", "/login"):
        r = client.get(path)
        assert r.status_code == 200, path
        body = r.text
        for pat in FORBIDDEN:
            assert re.search(pat, body, re.I) is None, f"{path} leaked {pat}"


def test_dfy_has_no_dummy_placeholders():
    r = client.get("/dfy")
    assert r.status_code == 200
    # Fake demo identities must not appear as placeholders
    for banned in ("Jordan Lee", "Lee Digital", "you@company.com", "Acme"):
        assert banned not in r.text


def test_footer_status_not_api_health():
    r = client.get("/")
    assert 'href="/status"' in r.text
    assert 'href="/api/health"' not in r.text
