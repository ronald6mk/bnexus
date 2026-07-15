"""ProposalForge FastAPI application."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from io import BytesIO
from datetime import datetime, timezone

from app import __version__
from app.auth import (
    SESSION_COOKIE,
    clear_session_cookie,
    create_session,
    destroy_session,
    hash_password,
    session_from_request,
    set_session_cookie,
    verify_password,
)
from app.db import DATA_DIR, get_connection, init_db, row_to_dict
from app.generator import content_to_sample_text, generate_proposal
from app.limits import can_create_proposal, usage_summary
from app.metrics import track
from app.models import BUDGET_RANGES, INDUSTRIES, PRICING, TIMELINES
from app.pdf_export import build_proposal_pdf

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DFY_ORDERS_PATH = DATA_DIR / "dfy_orders.json"
SAMPLES_DIR = ROOT / "samples"

app = FastAPI(title="ProposalForge", version=__version__)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_any(*names: str, default: str = "") -> str:
    """First non-empty env among aliases (supports operator typos / renames)."""
    for name in names:
        val = os.environ.get(name, "").strip()
        if val:
            return val
    return default


def app_secret() -> str:
    """Session / signing secret. Accepts PROPOSALFORGE_SECRET or PROPOSALFORGESECRET."""
    return _env_any(
        "PROPOSALFORGE_SECRET",
        "PROPOSALFORGESECRET",  # registered: operator set this on Render
        "BNEXUS_SECRET",
        default="dev-insecure-change-me",
    )


def payment_links() -> dict[str, str]:
    return {
        "pro": _env("PAYMENT_LINK_PRO", "#pricing"),
        "lifetime": _env("PAYMENT_LINK_LIFETIME", "#pricing"),
        "dfy": _env("PAYMENT_LINK_DFY", "/dfy"),
    }


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    if not DFY_ORDERS_PATH.exists():
        DFY_ORDERS_PATH.write_text("[]", encoding="utf-8")
    # Optional bootstrap Pro user via env
    admin_email = _env("ADMIN_PRO_EMAIL")
    if admin_email:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE users SET is_pro = 1 WHERE lower(email) = lower(?)",
                (admin_email,),
            )
            conn.commit()
        finally:
            conn.close()


def current_user(request: Request) -> Optional[dict[str, Any]]:
    sess = session_from_request(request)
    if not sess:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (sess["user_id"],)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        # Dependency-style raise via redirect handled in routes
        raise PermissionError("auth_required")
    return user


def _flash_ctx(request: Request, **extra: Any) -> dict[str, Any]:
    user = current_user(request)
    return {
        "request": request,
        "user": user,
        "pricing": PRICING,
        "payment_links": payment_links(),
        "industries": INDUSTRIES,
        "budget_ranges": BUDGET_RANGES,
        "timelines": TIMELINES,
        "version": __version__,
        **extra,
    }


# ---------- Health ----------


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "product": "proposalforge",
        "version": __version__,
        "offline_generator": True,
    }


# ---------- Public pages ----------


@app.get("/", response_class=HTMLResponse)
def landing(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "landing.html",
        _flash_ctx(request, page="landing"),
    )


@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "landing.html",
        _flash_ctx(request, page="pricing", scroll_pricing=True),
    )


@app.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request) -> HTMLResponse:
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        "auth.html",
        _flash_ctx(request, mode="signup", error=None),
    )


@app.post("/signup")
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    company_name: str = Form(""),
):
    email = email.strip().lower()
    if len(password) < 6:
        return templates.TemplateResponse(
            "auth.html",
            _flash_ctx(request, mode="signup", error="Password must be at least 6 characters."),
            status_code=400,
        )
    if "@" not in email:
        return templates.TemplateResponse(
            "auth.html",
            _flash_ctx(request, mode="signup", error="Enter a valid email."),
            status_code=400,
        )
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            return templates.TemplateResponse(
                "auth.html",
                _flash_ctx(request, mode="signup", error="Email already registered. Log in instead."),
                status_code=400,
            )
        is_pro = 1 if email == _env("ADMIN_PRO_EMAIL").lower() and _env("ADMIN_PRO_EMAIL") else 0
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, company_name, is_pro)
            VALUES (?, ?, ?, ?)
            """,
            (email, hash_password(password), company_name.strip(), is_pro),
        )
        conn.commit()
        user_id = int(cur.lastrowid)
    finally:
        conn.close()

    track("signup", email=email)
    token = create_session(user_id, email)
    resp = RedirectResponse("/dashboard", status_code=303)
    set_session_cookie(resp, token)
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        "auth.html",
        _flash_ctx(request, mode="login", error=None),
    )


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        user = row_to_dict(row)
    finally:
        conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "auth.html",
            _flash_ctx(request, mode="login", error="Invalid email or password."),
            status_code=401,
        )

    # Auto-promote admin
    if _env("ADMIN_PRO_EMAIL") and email == _env("ADMIN_PRO_EMAIL").lower() and not user["is_pro"]:
        conn = get_connection()
        try:
            conn.execute("UPDATE users SET is_pro = 1 WHERE id = ?", (user["id"],))
            conn.commit()
            user["is_pro"] = 1
        finally:
            conn.close()

    track("login", email=email)
    token = create_session(int(user["id"]), email)
    resp = RedirectResponse("/dashboard", status_code=303)
    set_session_cookie(resp, token)
    return resp


@app.post("/logout")
@app.get("/logout")
def logout(request: Request) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    destroy_session(token)
    resp = RedirectResponse("/", status_code=303)
    clear_session_cookie(resp)
    return resp


# ---------- Dashboard & proposals ----------


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, client_name, client_company, industry, status, created_at, updated_at
            FROM proposals WHERE user_id = ? ORDER BY updated_at DESC
            """,
            (user["id"],),
        ).fetchall()
        proposals = [dict(r) for r in rows]
        usage = usage_summary(user, conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        "dashboard.html",
        _flash_ctx(request, proposals=proposals, usage=usage),
    )


@app.get("/proposals/new", response_class=HTMLResponse)
def new_proposal_form(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        allowed, msg = can_create_proposal(user, conn)
        usage = usage_summary(user, conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        "proposal_form.html",
        _flash_ctx(
            request,
            allowed=allowed,
            limit_message=msg,
            usage=usage,
            form={},
            error=None if allowed else msg,
        ),
    )


@app.post("/proposals/new")
def create_proposal(
    request: Request,
    client_name: str = Form(...),
    client_company: str = Form(""),
    industry: str = Form("custom_ict"),
    services: str = Form(""),
    goals: str = Form(""),
    budget_range: str = Form("To be discussed"),
    timeline: str = Form("Flexible / TBD"),
    differentiators: str = Form(""),
    company_name: str = Form(""),
    brand_color: str = Form(""),
    sender_name: str = Form(""),
    sender_email: str = Form(""),
    sender_phone: str = Form(""),
):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = {
        "client_name": client_name,
        "client_company": client_company,
        "industry": industry,
        "services": services,
        "goals": goals,
        "budget_range": budget_range,
        "timeline": timeline,
        "differentiators": differentiators,
        "company_name": company_name,
        "brand_color": brand_color,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "sender_phone": sender_phone,
    }

    conn = get_connection()
    try:
        allowed, msg = can_create_proposal(user, conn)
        if not allowed:
            usage = usage_summary(user, conn)
            return templates.TemplateResponse(
                "proposal_form.html",
                _flash_ctx(
                    request,
                    allowed=False,
                    limit_message=msg,
                    usage=usage,
                    form=form,
                    error=msg,
                ),
                status_code=403,
            )

        # Persist brand fields on user profile if provided
        brand = company_name.strip() or user.get("company_name") or "Your Company"
        color = brand_color.strip() or user.get("brand_color") or "#1a56db"
        sname = sender_name.strip() or user.get("sender_name") or ""
        semail = sender_email.strip() or user.get("sender_email") or user.get("email") or ""
        sphone = sender_phone.strip() or user.get("sender_phone") or ""
        conn.execute(
            """
            UPDATE users SET company_name = ?, brand_color = ?,
                sender_name = ?, sender_email = ?, sender_phone = ?
            WHERE id = ?
            """,
            (brand, color, sname, semail, sphone, user["id"]),
        )

        content = generate_proposal(
            client_name=client_name.strip(),
            client_company=client_company.strip(),
            industry=industry,
            services=services,
            goals=goals,
            budget_range=budget_range,
            timeline=timeline,
            differentiators=differentiators,
            sender_company=brand,
            sender_name=sname,
        )
        title = content.get("title") or f"Proposal — {client_name}"

        cur = conn.execute(
            """
            INSERT INTO proposals (
                user_id, title, client_name, client_company, industry,
                services, goals, budget_range, timeline, differentiators,
                content_json, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', datetime('now'))
            """,
            (
                user["id"],
                title,
                client_name.strip(),
                client_company.strip(),
                industry,
                services.strip(),
                goals.strip(),
                budget_range,
                timeline,
                differentiators.strip(),
                json.dumps(content),
            ),
        )
        conn.commit()
        pid = int(cur.lastrowid)

        # Sample text file
        sample_path = SAMPLES_DIR / f"proposal_{pid}.txt"
        sample_path.write_text(content_to_sample_text(content), encoding="utf-8")
    finally:
        conn.close()

    track("generate", proposal_id=pid, industry=industry)
    return RedirectResponse(f"/proposals/{pid}", status_code=303)


@app.get("/proposals/{proposal_id}", response_class=HTMLResponse)
def view_proposal(request: Request, proposal_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ? AND user_id = ?",
            (proposal_id, user["id"]),
        ).fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=303)
        proposal = dict(row)
        content = json.loads(proposal["content_json"] or "{}")
        usage = usage_summary(user, conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        "proposal_view.html",
        _flash_ctx(request, proposal=proposal, content=content, usage=usage, saved=False),
    )


@app.post("/proposals/{proposal_id}")
async def update_proposal(request: Request, proposal_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ? AND user_id = ?",
            (proposal_id, user["id"]),
        ).fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=303)
        proposal = dict(row)
        content = json.loads(proposal["content_json"] or "{}")

        content["executive_summary"] = str(form.get("executive_summary") or content.get("executive_summary", ""))
        content["understanding"] = str(form.get("understanding") or content.get("understanding", ""))
        content["approach"] = str(form.get("approach") or content.get("approach", ""))
        content["why_us"] = str(form.get("why_us") or content.get("why_us", ""))
        content["next_steps"] = str(form.get("next_steps") or content.get("next_steps", ""))
        content["terms_note"] = str(form.get("terms_note") or content.get("terms_note", ""))

        # Rebuild investment from parallel fields
        names = form.getlist("item_name")
        descs = form.getlist("item_desc")
        amounts = form.getlist("item_amount")
        investment = []
        for i, name in enumerate(names):
            name = str(name).strip()
            if not name:
                continue
            try:
                amt = int(float(str(amounts[i] if i < len(amounts) else 0).replace(",", "") or 0))
            except (ValueError, TypeError):
                amt = 0
            investment.append(
                {
                    "name": name,
                    "description": str(descs[i] if i < len(descs) else ""),
                    "amount": amt,
                }
            )
        if investment:
            content["investment"] = investment
            content["investment_total"] = sum(int(x["amount"]) for x in investment)

        # Scope titles
        scope_titles = form.getlist("scope_title")
        scope_details = form.getlist("scope_detail")
        if scope_titles:
            content["scope"] = [
                {
                    "title": str(scope_titles[i]).strip(),
                    "detail": str(scope_details[i] if i < len(scope_details) else "").strip(),
                }
                for i in range(len(scope_titles))
                if str(scope_titles[i]).strip()
            ]

        title = str(form.get("title") or proposal["title"]).strip()
        conn.execute(
            """
            UPDATE proposals SET title = ?, content_json = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (title, json.dumps(content), proposal_id, user["id"]),
        )
        conn.commit()
        proposal["title"] = title
        proposal["content_json"] = json.dumps(content)
        usage = usage_summary(user, conn)
    finally:
        conn.close()

    return templates.TemplateResponse(
        "proposal_view.html",
        _flash_ctx(
            request,
            proposal=proposal,
            content=content,
            usage=usage,
            saved=True,
        ),
    )


@app.get("/proposals/{proposal_id}/pdf")
def download_pdf(request: Request, proposal_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ? AND user_id = ?",
            (proposal_id, user["id"]),
        ).fetchone()
        if not row:
            return RedirectResponse("/dashboard", status_code=303)
        proposal = dict(row)
        content = json.loads(proposal["content_json"] or "{}")
    finally:
        conn.close()

    is_pro = bool(user.get("is_pro"))
    pdf_bytes = build_proposal_pdf(
        content,
        brand_name=user.get("company_name") or "ProposalForge",
        brand_color=user.get("brand_color") or "#1a56db",
        client_name=proposal.get("client_name") or "",
        client_company=proposal.get("client_company") or "",
        watermark=not is_pro,
        sender_name=user.get("sender_name") or "",
        sender_email=user.get("sender_email") or user.get("email") or "",
        sender_phone=user.get("sender_phone") or "",
    )
    track("download", proposal_id=proposal_id, watermark=not is_pro)
    filename = f"proposal_{proposal_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/proposals/{proposal_id}/delete")
def delete_proposal(request: Request, proposal_id: int):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM proposals WHERE id = ? AND user_id = ?",
            (proposal_id, user["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/dashboard", status_code=303)


# ---------- DFY orders (first-cash path without payment processor) ----------


@app.get("/dfy", response_class=HTMLResponse)
def dfy_form(request: Request):
    return templates.TemplateResponse(
        "dfy.html",
        _flash_ctx(request, success=None, error=None),
    )


@app.post("/dfy")
def dfy_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    package: str = Form("standard"),
    client_context: str = Form(""),
    notes: str = Form(""),
):
    package = package if package in ("standard", "premium") else "standard"
    price = 49 if package == "standard" else 99
    order = {
        "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "name": name.strip(),
        "email": email.strip().lower(),
        "company": company.strip(),
        "package": package,
        "price_usd": price,
        "client_context": client_context.strip(),
        "notes": notes.strip(),
        "status": "new",
        "payment_note": "Manual — confirm payment offline / Lemon Squeezy link when configured",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    orders: list = []
    if DFY_ORDERS_PATH.exists():
        try:
            orders = json.loads(DFY_ORDERS_PATH.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            orders = []
    orders.append(order)
    DFY_ORDERS_PATH.write_text(json.dumps(orders, indent=2), encoding="utf-8")
    track("dfy", package=package, price_usd=price)
    return templates.TemplateResponse(
        "dfy.html",
        _flash_ctx(
            request,
            success=(
                f"DFY order logged (#{order['id']}, ${price} {package}). "
                f"We'll follow up at {order['email']}. "
                "Payment: use the configured PAYMENT_LINK_DFY or settle manually."
            ),
            error=None,
        ),
    )


# ---------- Settings (promote self via secret for demo) ----------


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_connection()
    try:
        usage = usage_summary(user, conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        "settings.html",
        _flash_ctx(request, usage=usage, message=None),
    )


@app.post("/settings")
def settings_save(
    request: Request,
    company_name: str = Form(""),
    brand_color: str = Form("#1a56db"),
    sender_name: str = Form(""),
    sender_email: str = Form(""),
    sender_phone: str = Form(""),
    pro_code: str = Form(""),
):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    msg = "Settings saved."
    is_pro = int(user.get("is_pro") or 0)
    # Demo unlock: set PRO_UNLOCK_CODE env (default proposalforge-pro)
    unlock = _env("PRO_UNLOCK_CODE", "proposalforge-pro")
    if pro_code.strip() and pro_code.strip() == unlock:
        is_pro = 1
        msg = "Settings saved. Pro unlocked for this account."
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE users SET company_name=?, brand_color=?, sender_name=?,
                sender_email=?, sender_phone=?, is_pro=?
            WHERE id=?
            """,
            (
                company_name.strip(),
                brand_color.strip() or "#1a56db",
                sender_name.strip(),
                sender_email.strip(),
                sender_phone.strip(),
                is_pro,
                user["id"],
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        user = dict(row) if row else user
        usage = usage_summary(user, conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        "settings.html",
        _flash_ctx(request, usage=usage, message=msg, user=user),
    )
