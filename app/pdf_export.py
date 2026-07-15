"""Branded PDF export via fpdf2."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fpdf import FPDF


class ProposalPDF(FPDF):
    def __init__(
        self,
        brand_name: str = "ProposalForge",
        brand_color: tuple[int, int, int] = (26, 86, 219),
        watermark: bool = False,
    ):
        super().__init__()
        self.brand_name = brand_name
        self.brand_color = brand_color
        self.watermark = watermark
        self.set_auto_page_break(auto=True, margin=22)

    def header(self) -> None:
        self.set_fill_color(*self.brand_color)
        self.rect(0, 0, 210, 12, "F")
        self.set_y(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, self.brand_name[:60], align="L")
        self.ln(14)
        self.set_text_color(30, 30, 30)

    def footer(self) -> None:
        self.set_y(-18)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(100, 100, 100)
        self.multi_cell(
            0,
            3.5,
            "Disclaimer: This proposal is not legal advice and does not create a binding contract. "
            "Confirm commercial terms in a separate agreement. | Page "
            f"{self.page_no()}/{{nb}}",
            align="C",
        )

    def _draw_watermark(self) -> None:
        if not self.watermark:
            return
        self.set_font("Helvetica", "B", 48)
        self.set_text_color(220, 220, 220)
        with self.rotation(45, x=105, y=150):
            self.text(40, 150, "ProposalForge FREE")
        self.set_text_color(30, 30, 30)

    def section_title(self, title: str) -> None:
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*self.brand_color)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self.brand_color)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(30, 30, 30)

    def body_text(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text or "")
        self.ln(2)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or "#1a56db").lstrip("#")
    if len(h) != 6:
        return (26, 86, 219)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return (26, 86, 219)


def _safe(text: Any) -> str:
    """FPDF core fonts need latin-1-ish; replace common unicode."""
    s = str(text or "")
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def build_proposal_pdf(
    content: dict[str, Any],
    *,
    brand_name: str = "ProposalForge",
    brand_color: str = "#1a56db",
    client_name: str = "",
    client_company: str = "",
    watermark: bool = False,
    sender_name: str = "",
    sender_email: str = "",
    sender_phone: str = "",
) -> bytes:
    pdf = ProposalPDF(
        brand_name=_safe(brand_name) or "ProposalForge",
        brand_color=_hex_to_rgb(brand_color),
        watermark=watermark,
    )
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf._draw_watermark()

    title = _safe(content.get("title") or "Client Proposal")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_hex_to_rgb(brand_color))
    pdf.multi_cell(0, 9, title)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    prepared = f"Prepared for: {_safe(client_name)}"
    if client_company:
        prepared += f" ({_safe(client_company)})"
    pdf.cell(0, 6, prepared, new_x="LMARGIN", new_y="NEXT")
    contact_bits = [x for x in [sender_name, sender_email, sender_phone] if x]
    if contact_bits:
        pdf.cell(0, 6, f"From: {_safe(' | '.join(contact_bits))}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.section_title("1. Executive Summary")
    pdf.body_text(_safe(content.get("executive_summary", "")))

    pdf.section_title("2. Understanding Your Needs")
    pdf.body_text(_safe(content.get("understanding", "")))

    pdf.section_title("3. Scope of Work")
    for item in content.get("scope") or []:
        if isinstance(item, dict):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 5, _safe(f"- {item.get('title', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 4.5, _safe(item.get("detail", "")))
            pdf.set_text_color(30, 30, 30)
        else:
            pdf.body_text(_safe(f"- {item}"))
    pdf.ln(2)

    pdf.section_title("4. Approach")
    pdf.body_text(_safe(content.get("approach", "")))

    pdf.section_title("5. Timeline")
    for ph in content.get("timeline_phases") or []:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, _safe(ph.get("name", "Phase")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4.5, _safe(ph.get("description", "")))
        pdf.ln(1)

    pdf.section_title("6. Investment (Indicative)")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 244, 255)
    pdf.cell(100, 7, "Item", border=1, fill=True)
    pdf.cell(50, 7, "Description", border=1, fill=True)
    pdf.cell(30, 7, "Amount", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for inv in content.get("investment") or []:
        name = _safe(inv.get("name", ""))[:40]
        desc = _safe(inv.get("description", ""))[:28]
        amt = f"${int(inv.get('amount', 0)):,}"
        pdf.cell(100, 6, name, border=1)
        pdf.cell(50, 6, desc, border=1)
        pdf.cell(30, 6, amt, border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    total = content.get("investment_total")
    if total is None:
        total = sum(int(i.get("amount", 0)) for i in (content.get("investment") or []))
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(150, 7, "Indicative total", border=1)
    pdf.cell(30, 7, f"${int(total):,}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.section_title("7. Why Work With Us")
    pdf.body_text(_safe(content.get("why_us", "")))

    pdf.section_title("8. Next Steps")
    pdf.body_text(_safe(content.get("next_steps", "")))

    pdf.section_title("9. Terms & Notes")
    pdf.body_text(_safe(content.get("terms_note", "")))

    out = BytesIO()
    pdf.output(out)
    return out.getvalue()
