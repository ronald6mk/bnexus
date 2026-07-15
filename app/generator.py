"""Offline rule-based proposal composer (no API keys required)."""

from __future__ import annotations

from typing import Any

from app.models import INDUSTRIES


def _split_list(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    parts: list[str] = []
    for chunk in text.replace(";", "\n").replace(",", "\n").split("\n"):
        item = chunk.strip(" \t-•*")
        if item:
            parts.append(item)
    return parts


def _estimate_line_items(industry: str, services: list[str], budget_range: str) -> list[dict[str, Any]]:
    """Heuristic investment table from industry + services + budget hint."""
    budget_mid = {
        "Under $2,000": 1500,
        "$2,000 – $5,000": 3500,
        "$5,000 – $15,000": 9000,
        "$15,000 – $50,000": 28000,
        "$50,000+": 60000,
        "To be discussed": 5000,
    }.get(budget_range, 5000)

    if not services:
        services = {
            "web": ["Discovery & UX", "Design system", "Frontend build", "CMS / backend", "QA & launch"],
            "it_retainer": ["Onboarding audit", "Monitoring setup", "Monthly support hours", "Security baseline"],
            "consulting": ["Discovery workshop", "Current-state assessment", "Roadmap & recommendations", "Handover pack"],
            "custom_ict": ["Requirements workshop", "Solution design", "Implementation", "Training & handover"],
        }.get(industry, ["Discovery", "Delivery", "Handover"])

    n = max(len(services), 1)
    weights = [1.0] * n
    # Slightly weight first (discovery) and last (launch) differently
    if n >= 3:
        weights[0] = 0.85
        weights[-1] = 0.9
    total_w = sum(weights)
    items: list[dict[str, Any]] = []
    running = 0
    for i, (svc, w) in enumerate(zip(services, weights)):
        if i == n - 1:
            amount = max(budget_mid - running, 100)
        else:
            amount = max(int(round(budget_mid * (w / total_w) / 50) * 50), 100)
            running += amount
        items.append(
            {
                "name": svc,
                "description": f"Scoped delivery for: {svc}",
                "amount": amount,
            }
        )
    return items


def _timeline_phases(industry: str, timeline: str, services: list[str]) -> list[dict[str, str]]:
    base = {
        "web": [
            ("Discover", "Stakeholder interviews, goals, success metrics, content inventory."),
            ("Design", "Wireframes, visual design, component library, client review."),
            ("Build", "Frontend/backend implementation, integrations, content entry."),
            ("Launch", "QA, performance, training, go-live support."),
        ],
        "it_retainer": [
            ("Onboard", "Asset inventory, access, tooling, baseline health check."),
            ("Stabilize", "Monitoring, backups, patch policy, documentation."),
            ("Operate", "Ticket triage, monthly reporting, continuous improvement."),
            ("Review", "Quarterly business review and roadmap refresh."),
        ],
        "consulting": [
            ("Discover", "Workshops, data collection, stakeholder mapping."),
            ("Analyze", "Gap analysis, risk/cost model, option comparison."),
            ("Recommend", "Prioritized roadmap, investment cases, decision pack."),
            ("Enable", "Presentation, Q&A, optional implementation advisory."),
        ],
        "custom_ict": [
            ("Define", "Requirements, constraints, success criteria."),
            ("Design", "Architecture, estimates, risk register."),
            ("Deliver", "Build, configure, integrate, iterate with feedback."),
            ("Handover", "Docs, training, warranty/support window."),
        ],
    }.get(industry, [])

    if not base:
        base = [
            ("Phase 1", "Kickoff and discovery."),
            ("Phase 2", "Core delivery."),
            ("Phase 3", "Review and handover."),
        ]

    # Annotate with overall timeline
    phases = []
    for name, desc in base:
        phases.append(
            {
                "name": name,
                "description": f"{desc} Overall target: {timeline or 'agreed timeline'}.",
            }
        )
    if services and len(services) <= 4:
        # Light customization note
        phases[0]["description"] += f" Priority focus: {', '.join(services[:3])}."
    return phases


def generate_proposal(
    *,
    client_name: str,
    client_company: str = "",
    industry: str = "custom_ict",
    services: str = "",
    goals: str = "",
    budget_range: str = "To be discussed",
    timeline: str = "Flexible / TBD",
    differentiators: str = "",
    sender_company: str = "Your Company",
    sender_name: str = "",
) -> dict[str, Any]:
    """
    Compose a full proposal content structure offline from templates + inputs.
    Returns dict matching models.empty_proposal_content shape (+ meta).
    """
    industry_key = industry if industry in INDUSTRIES else "custom_ict"
    industry_label = INDUSTRIES[industry_key]
    client_label = client_company.strip() or client_name.strip() or "the Client"
    svc_list = _split_list(services)
    goal_list = _split_list(goals)
    diff_list = _split_list(differentiators)
    brand = sender_company.strip() or "Our team"
    contact = sender_name.strip() or brand

    goals_text = (
        "; ".join(goal_list)
        if goal_list
        else "improve operational efficiency, reduce risk, and deliver measurable business outcomes"
    )
    svc_text = ", ".join(svc_list) if svc_list else industry_label.lower()

    executive_summary = (
        f"{brand} is pleased to present this proposal to {client_label}. "
        f"This engagement focuses on {svc_text} within the {industry_label} domain. "
        f"Our objective is to help {client_name or client_label} achieve: {goals_text}. "
        f"Suggested investment range: {budget_range or 'to be confirmed'}. "
        f"Indicative timeline: {timeline or 'to be agreed'}."
    )

    understanding = (
        f"We understand that {client_label} is seeking a practical partner for {industry_label.lower()}. "
        f"Key outcomes discussed include: {goals_text}. "
        f"We have structured this proposal so scope, investment, and next steps are clear and decision-ready."
    )

    scope_items = svc_list or [
        f"{industry_label} discovery and scoping",
        "Solution design and delivery plan",
        "Implementation / advisory as agreed",
        "Documentation and knowledge transfer",
    ]
    scope = [{"title": s, "detail": f"Included as part of the agreed {industry_label} engagement."} for s in scope_items]

    approach = (
        f"{brand} uses a structured, low-risk delivery approach: clarify outcomes, "
        f"agree scope and success metrics, deliver in visible increments, and handover with documentation. "
        f"You will have a named contact ({contact}) and regular progress checkpoints."
    )

    why_parts = [
        f"{brand} specializes in practical ICT delivery for freelancers and small agencies' clients.",
        "Clear written proposals reduce sales friction and set professional expectations.",
    ]
    if diff_list:
        why_parts.append("Differentiators for this engagement: " + "; ".join(diff_list) + ".")
    else:
        why_parts.append(
            "We emphasize transparent pricing, scoped deliverables, and proposals you can send the same day."
        )
    why_us = " ".join(why_parts)

    next_steps = (
        "1) Review this proposal and mark any scope adjustments. "
        "2) Confirm budget band and preferred start date. "
        "3) Sign / accept (or reply in writing) to lock the engagement. "
        f"4) Kickoff call with {contact} to finalize access and success metrics."
    )

    terms_note = (
        "This proposal is an estimate based on information provided and is not a binding contract or legal advice. "
        "Final terms, payment schedule, IP ownership, and SLAs will be confirmed in a separate agreement or SOW. "
        "Pricing is indicative and may change if scope changes materially. Valid for 30 days unless otherwise stated."
    )

    investment = _estimate_line_items(industry_key, svc_list, budget_range or "To be discussed")
    total = sum(int(i["amount"]) for i in investment)

    title = f"{industry_label} Proposal — {client_label}"

    return {
        "title": title,
        "meta": {
            "client_name": client_name,
            "client_company": client_company,
            "industry": industry_key,
            "industry_label": industry_label,
            "budget_range": budget_range,
            "timeline": timeline,
            "sender_company": brand,
        },
        "executive_summary": executive_summary,
        "understanding": understanding,
        "scope": scope,
        "approach": approach,
        "timeline_phases": _timeline_phases(industry_key, timeline, svc_list),
        "investment": investment,
        "investment_total": total,
        "why_us": why_us,
        "next_steps": next_steps,
        "terms_note": terms_note,
    }


def content_to_sample_text(content: dict[str, Any]) -> str:
    """Render proposal content to plain text (for samples/)."""
    lines = [
        content.get("title") or "Proposal",
        "=" * 60,
        "",
        "EXECUTIVE SUMMARY",
        content.get("executive_summary", ""),
        "",
        "UNDERSTANDING",
        content.get("understanding", ""),
        "",
        "SCOPE",
    ]
    for item in content.get("scope") or []:
        if isinstance(item, dict):
            lines.append(f"- {item.get('title', '')}: {item.get('detail', '')}")
        else:
            lines.append(f"- {item}")
    lines += ["", "APPROACH", content.get("approach", ""), "", "TIMELINE"]
    for ph in content.get("timeline_phases") or []:
        lines.append(f"- {ph.get('name', '')}: {ph.get('description', '')}")
    lines += ["", "INVESTMENT"]
    for inv in content.get("investment") or []:
        lines.append(f"- {inv.get('name', '')}: ${inv.get('amount', 0):,}")
    if content.get("investment_total") is not None:
        lines.append(f"TOTAL (indicative): ${content['investment_total']:,}")
    lines += [
        "",
        "WHY US",
        content.get("why_us", ""),
        "",
        "NEXT STEPS",
        content.get("next_steps", ""),
        "",
        "TERMS",
        content.get("terms_note", ""),
        "",
        "Disclaimer: This document is not legal advice.",
    ]
    return "\n".join(lines)
