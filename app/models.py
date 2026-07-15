"""Domain helpers / constants for ProposalForge (SQLite row dicts used at runtime)."""

from __future__ import annotations

from typing import Any

INDUSTRIES = {
    "web": "Web Development",
    "it_retainer": "IT Retainer / Managed Services",
    "consulting": "ICT Consulting",
    "custom_ict": "Custom ICT Project",
}

BUDGET_RANGES = [
    "Under $2,000",
    "$2,000 – $5,000",
    "$5,000 – $15,000",
    "$15,000 – $50,000",
    "$50,000+",
    "To be discussed",
]

TIMELINES = [
    "1–2 weeks",
    "2–4 weeks",
    "1–2 months",
    "2–3 months",
    "3+ months",
    "Flexible / TBD",
]

PRICING = {
    "free": {
        "name": "Free",
        "price": "$0",
        "period": "/mo",
        "limit": "3 proposals / month",
        "features": [
            "3 proposals per calendar month",
            "Offline template generator",
            "Branded PDF export (watermark on free)",
            "Edit sections & line items",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": "$15",
        "period": "/mo",
        "limit": "Unlimited",
        "features": [
            "Unlimited proposals",
            "No watermark",
            "Branded PDFs",
            "Priority template updates",
        ],
    },
    "lifetime": {
        "name": "Lifetime",
        "price": "$89",
        "period": " one-time",
        "limit": "Unlimited forever",
        "features": [
            "Everything in Pro",
            "One-time payment",
            "Lifetime updates for this product line",
        ],
    },
    "dfy": {
        "name": "Done-For-You",
        "price": "$49 / $99",
        "period": "",
        "limit": "Human-written proposal",
        "features": [
            "$49 standard DFY proposal",
            "$99 premium DFY + discovery call notes",
            "We write it — you send it",
        ],
    },
}


def empty_proposal_content() -> dict[str, Any]:
    return {
        "executive_summary": "",
        "understanding": "",
        "scope": [],
        "approach": "",
        "timeline_phases": [],
        "investment": [],
        "why_us": "",
        "next_steps": "",
        "terms_note": "",
    }
