"""Write samples/invoice.pdf: a made-up Belgian invoice with a header, line items, totals and a payment footer.

Run it with: uv run --with reportlab scripts/make_sample_invoice.py
The companies, numbers and bank account are fictional.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).resolve().parents[1] / "samples" / "invoice.pdf"
INK = colors.HexColor("#1c1c1e")
MUTED = colors.HexColor("#62626a")
ACCENT = colors.HexColor("#1f4e79")
RULE = colors.HexColor("#d5d5d0")

ITEMS = [
    ("Azure architecture workshop (per day)", 2, 1250.00),
    ("Document extraction proof of concept (per day)", 5, 980.00),
    ("Travel expenses Gent - Antwerpen", 1, 142.50),
    ("Azure consumption October 2026", 1, 386.20),
]
VAT_RATE = 21


def money(value: float) -> str:
    """1234.5 -> '1.234,50' (Belgian notation)."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def lines(c: Canvas, x: float, y: float, rows: list[str], size: float = 9.5, leading: float = 13) -> float:
    c.setFont("Helvetica", size)
    for row in rows:
        c.drawString(x, y, row)
        y -= leading
    return y


def label(c: Canvas, x: float, y: float, text: str) -> None:
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(MUTED)
    c.drawString(x, y, text.upper())
    c.setFillColor(INK)


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    c = Canvas(str(OUT), pagesize=A4)
    c.setTitle("Invoice 2026-0147")
    width, height = A4
    left, right = 20 * mm, width - 20 * mm

    # --- header: vendor on the left, the word INVOICE and its numbers on the right
    c.setFillColor(ACCENT)
    c.rect(left, height - 27 * mm, 9 * mm, 9 * mm, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left + 12 * mm, height - 24.5 * mm, "Noordzee Consulting BV")
    c.setFillColor(INK)
    lines(
        c,
        left,
        height - 34 * mm,
        ["Korenmarkt 14", "9000 Gent, Belgium", "VAT BE 0712.345.678", "info@noordzee-consulting.example"],
    )

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(ACCENT)
    c.drawRightString(right, height - 25 * mm, "INVOICE")
    c.setFillColor(INK)
    meta = [
        ("Invoice number", "2026-0147"),
        ("Invoice date", "3 November 2026"),
        ("Due date", "3 December 2026"),
        ("Purchase order", "PO-88213"),
    ]
    y = height - 34 * mm
    for key, value in meta:
        c.setFont("Helvetica", 9.5)
        c.setFillColor(MUTED)
        c.drawRightString(right - 38 * mm, y, key)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawRightString(right, y, value)
        y -= 13

    # --- customer
    y = height - 66 * mm
    label(c, left, y, "Bill to")
    lines(
        c,
        left,
        y - 14,
        ["Atelier Lumen NV", "Attn. Accounts Payable", "Meir 102", "2000 Antwerpen, Belgium", "VAT BE 0456.789.123"],
    )

    # --- line items
    cols = {"desc": left, "qty": 118 * mm, "unit": 143 * mm, "vat": 160 * mm, "amount": right}
    y = height - 108 * mm
    c.setFillColor(ACCENT)
    c.rect(left, y - 3 * mm, right - left, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(cols["desc"] + 2 * mm, y, "Description")
    c.drawRightString(cols["qty"], y, "Qty")
    c.drawRightString(cols["unit"], y, "Unit price")
    c.drawRightString(cols["vat"], y, "VAT")
    c.drawRightString(cols["amount"] - 2 * mm, y, "Amount")
    c.setFillColor(INK)

    subtotal = 0.0
    y -= 11 * mm
    for description, quantity, unit_price in ITEMS:
        amount = quantity * unit_price
        subtotal += amount
        c.setFont("Helvetica", 9.5)
        c.drawString(cols["desc"] + 2 * mm, y, description)
        c.drawRightString(cols["qty"], y, str(quantity))
        c.drawRightString(cols["unit"], y, money(unit_price))
        c.drawRightString(cols["vat"], y, f"{VAT_RATE}%")
        c.drawRightString(cols["amount"] - 2 * mm, y, money(amount))
        c.setStrokeColor(RULE)
        c.line(left, y - 3.5 * mm, right, y - 3.5 * mm)
        y -= 9 * mm

    # --- totals
    vat = round(subtotal * VAT_RATE / 100, 2)
    total = subtotal + vat
    y -= 3 * mm
    for key, value in [("Subtotal", money(subtotal)), (f"VAT {VAT_RATE}%", money(vat))]:
        c.setFont("Helvetica", 9.5)
        c.drawRightString(cols["vat"], y, key)
        c.drawRightString(cols["amount"] - 2 * mm, y, value)
        y -= 6.5 * mm
    c.setStrokeColor(INK)
    c.line(cols["qty"], y + 3.5 * mm, right, y + 3.5 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(cols["vat"], y - 1.5 * mm, "Total due")
    c.drawRightString(cols["amount"] - 2 * mm, y - 1.5 * mm, f"EUR {money(total)}")

    # --- footer: how to pay
    y = 52 * mm
    c.setStrokeColor(RULE)
    c.line(left, y + 6 * mm, right, y + 6 * mm)
    label(c, left, y, "Payment details")
    lines(
        c,
        left,
        y - 14,
        ["IBAN BE68 5390 0754 7034", "BIC GKCCBEBB", "Structured reference +++147/2026/00381+++"],
    )
    label(c, 110 * mm, y, "Payment terms")
    lines(
        c,
        110 * mm,
        y - 14,
        ["Payment within 30 days of the invoice date.", "Late payments carry 8% interest per year."],
    )
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(
        width / 2,
        14 * mm,
        "Noordzee Consulting BV - Korenmarkt 14, 9000 Gent - RPR Gent - VAT BE 0712.345.678 - Page 1 of 1",
    )
    c.save()
    print(OUT)  # noqa: T201


if __name__ == "__main__":
    main()
