"""Write a made-up Belgian invoice as a PDF: a header, line items, totals and a payment footer.

    uv run --with reportlab scripts/make_sample_invoice.py               # samples/invoice.pdf, 4 line items
    uv run --with reportlab scripts/make_sample_invoice.py --items 100   # samples/invoice-100-items.pdf, several pages

With --items the lines are generated (fixed seed, so the file is the same every time) and the expected values are
written next to the PDF as JSON, to check an extraction against. The companies, numbers and bank account are
fictional.
"""

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
INK = colors.HexColor("#1c1c1e")
MUTED = colors.HexColor("#62626a")
ACCENT = colors.HexColor("#1f4e79")
RULE = colors.HexColor("#d5d5d0")

WIDTH, HEIGHT = A4
LEFT, RIGHT = 20 * mm, WIDTH - 20 * mm
COLS = {"desc": LEFT, "qty": 118 * mm, "unit": 143 * mm, "vat": 160 * mm, "amount": RIGHT}
ROWS_BOTTOM = 28 * mm  # no line item below this: the page footer sits under it
PAYMENT_TOP = 58 * mm  # the payment block of the last page starts here


@dataclass
class Item:
    description: str
    quantity: int
    unit_price: float
    vat_rate: int

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    number: str
    date: str
    due: str
    purchase_order: str
    items: list[Item]

    @property
    def subtotal(self) -> float:
        return round(sum(item.amount for item in self.items), 2)

    def vat_per_rate(self) -> dict[int, float]:
        rates = sorted({item.vat_rate for item in self.items}, reverse=True)
        return {r: round(sum(i.amount for i in self.items if i.vat_rate == r) * r / 100, 2) for r in rates}

    @property
    def vat(self) -> float:
        return round(sum(self.vat_per_rate().values()), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.vat, 2)


FIXED = Invoice(
    number="2026-0147",
    date="3 November 2026",
    due="3 December 2026",
    purchase_order="PO-88213",
    items=[
        Item("Azure architecture workshop (per day)", 2, 1250.00, 21),
        Item("Document extraction proof of concept (per day)", 5, 980.00, 21),
        Item("Travel expenses Gent - Antwerpen", 1, 142.50, 21),
        Item("Azure consumption October 2026", 1, 386.20, 21),
    ],
)

# what a generated line is made of: (description, lowest price, highest price, VAT rate)
CATALOG = [
    ("Consulting, senior architect (per hour)", 135, 165, 21),
    ("Consulting, data engineer (per hour)", 105, 125, 21),
    ("Workshop preparation (per hour)", 95, 110, 21),
    ("Azure OpenAI consumption", 40, 900, 21),
    ("Azure Container Apps consumption", 15, 240, 21),
    ("Azure AI Search, standard tier", 230, 250, 21),
    ("Storage account, hot tier", 4, 60, 21),
    ("Log Analytics ingestion", 8, 140, 21),
    ("Software licence, annual seat", 180, 420, 21),
    ("Support plan, monthly fee", 290, 310, 21),
    ("Training manual, printed", 18, 34, 6),
    ("Reference book, cloud architecture", 39, 72, 6),
    ("Train ticket Gent - Brussel", 9, 22, 6),
    ("Travel expenses, kilometre allowance", 12, 95, 21),
    ("Hotel night, project site", 110, 185, 6),
]
PERIODS = ["August 2026", "September 2026", "October 2026", "week 40", "week 41", "week 42", "week 43", "week 44"]


def generated(count: int) -> Invoice:
    rng = random.Random(count)  # noqa: S311  (test data, and the seed makes the same invoice every time)
    items = []
    for _ in range(count):
        description, low, high, vat_rate = rng.choice(CATALOG)
        price = round(rng.uniform(low, high), 2)
        items.append(Item(f"{description}, {rng.choice(PERIODS)}", rng.randint(1, 40), price, vat_rate))
    return Invoice("2026-0148", "5 November 2026", "5 December 2026", "PO-88240", items)


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


def first_page_header(c: Canvas, invoice: Invoice) -> float:
    """Vendor, the word INVOICE with its numbers, and the customer. Returns where the table starts."""
    c.setFillColor(ACCENT)
    c.rect(LEFT, HEIGHT - 27 * mm, 9 * mm, 9 * mm, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(LEFT + 12 * mm, HEIGHT - 24.5 * mm, "Noordzee Consulting BV")
    c.setFillColor(INK)
    lines(
        c,
        LEFT,
        HEIGHT - 34 * mm,
        ["Korenmarkt 14", "9000 Gent, Belgium", "VAT BE 0712.345.678", "info@noordzee-consulting.example"],
    )

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(ACCENT)
    c.drawRightString(RIGHT, HEIGHT - 25 * mm, "INVOICE")
    c.setFillColor(INK)
    meta = [
        ("Invoice number", invoice.number),
        ("Invoice date", invoice.date),
        ("Due date", invoice.due),
        ("Purchase order", invoice.purchase_order),
    ]
    y = HEIGHT - 34 * mm
    for key, value in meta:
        c.setFont("Helvetica", 9.5)
        c.setFillColor(MUTED)
        c.drawRightString(RIGHT - 38 * mm, y, key)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawRightString(RIGHT, y, value)
        y -= 13

    y = HEIGHT - 66 * mm
    label(c, LEFT, y, "Bill to")
    lines(
        c,
        LEFT,
        y - 14,
        ["Atelier Lumen NV", "Attn. Accounts Payable", "Meir 102", "2000 Antwerpen, Belgium", "VAT BE 0456.789.123"],
    )
    return HEIGHT - 108 * mm


def continued_header(c: Canvas, invoice: Invoice) -> float:
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ACCENT)
    c.drawString(LEFT, HEIGHT - 20 * mm, "Noordzee Consulting BV")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(RIGHT, HEIGHT - 20 * mm, f"Invoice {invoice.number} (continued)")
    c.setFillColor(INK)
    return HEIGHT - 32 * mm


def table_header(c: Canvas, y: float) -> None:
    c.setFillColor(ACCENT)
    c.rect(LEFT, y - 3 * mm, RIGHT - LEFT, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(COLS["desc"] + 2 * mm, y, "Description")
    c.drawRightString(COLS["qty"], y, "Qty")
    c.drawRightString(COLS["unit"], y, "Unit price")
    c.drawRightString(COLS["vat"], y, "VAT")
    c.drawRightString(COLS["amount"] - 2 * mm, y, "Amount")
    c.setFillColor(INK)


def item_row(c: Canvas, y: float, item: Item, row_height: float) -> None:
    c.setFont("Helvetica", 9.5 if row_height > 8 * mm else 9)
    c.drawString(COLS["desc"] + 2 * mm, y, item.description)
    c.drawRightString(COLS["qty"], y, str(item.quantity))
    c.drawRightString(COLS["unit"], y, money(item.unit_price))
    c.drawRightString(COLS["vat"], y, f"{item.vat_rate}%")
    c.drawRightString(COLS["amount"] - 2 * mm, y, money(item.amount))
    c.setStrokeColor(RULE)
    c.line(LEFT, y - row_height * 0.39, RIGHT, y - row_height * 0.39)


def totals(c: Canvas, y: float, invoice: Invoice) -> None:
    rows = [("Subtotal", money(invoice.subtotal))]
    per_rate = invoice.vat_per_rate()
    rows += [(f"VAT {rate}%", money(amount)) for rate, amount in per_rate.items()]
    if len(per_rate) > 1:
        rows.append(("Total VAT", money(invoice.vat)))
    for key, value in rows:
        c.setFont("Helvetica", 9.5)
        c.drawRightString(COLS["vat"], y, key)
        c.drawRightString(COLS["amount"] - 2 * mm, y, value)
        y -= 6.5 * mm
    c.setStrokeColor(INK)
    c.line(COLS["qty"], y + 3.5 * mm, RIGHT, y + 3.5 * mm)
    c.setFont("Helvetica-Bold", 11)
    amount = f"EUR {money(invoice.total)}"
    # a large total is wider than its column: keep the label clear of it
    label_right = min(COLS["vat"], COLS["amount"] - 2 * mm - c.stringWidth(amount, "Helvetica-Bold", 11) - 3 * mm)
    c.drawRightString(label_right, y - 1.5 * mm, "Total due")
    c.drawRightString(COLS["amount"] - 2 * mm, y - 1.5 * mm, amount)


def payment_block(c: Canvas, invoice: Invoice) -> None:
    y = 52 * mm
    c.setStrokeColor(RULE)
    c.line(LEFT, y + 6 * mm, RIGHT, y + 6 * mm)
    label(c, LEFT, y, "Payment details")
    reference = f"+++{invoice.number[-3:]}/2026/00381+++"
    lines(c, LEFT, y - 14, ["IBAN BE68 5390 0754 7034", "BIC GKCCBEBB", f"Structured reference {reference}"])
    label(c, 110 * mm, y, "Payment terms")
    lines(
        c,
        110 * mm,
        y - 14,
        ["Payment within 30 days of the invoice date.", "Late payments carry 8% interest per year."],
    )


def page_footer(c: Canvas, page: int, pages: int) -> None:
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(
        WIDTH / 2,
        14 * mm,
        f"Noordzee Consulting BV - Korenmarkt 14, 9000 Gent - RPR Gent - VAT BE 0712.345.678 - Page {page} of {pages}",
    )
    c.setFillColor(INK)


def paginate(items: list[Item], row_height: float, totals_height: float) -> list[list[Item]]:
    """The items per page. The last page also has to hold the totals above the payment block: when they do not
    fit under its last row, they get a page of their own (an empty list)."""
    first_top, next_top = HEIGHT - 119 * mm, HEIGHT - 43 * mm  # first row of a first / a continued page
    pages: list[list[Item]] = []
    rest = list(items)
    while rest:
        top = first_top if not pages else next_top
        fits = int((top - ROWS_BOTTOM) / row_height) + 1
        pages.append(rest[:fits])
        rest = rest[fits:]
    last_top = first_top if len(pages) == 1 else next_top
    after_last_row = last_top - len(pages[-1]) * row_height
    if after_last_row - totals_height < PAYMENT_TOP + 4 * mm:
        pages.append([])
    return pages


def draw(invoice: Invoice, out: Path) -> None:
    row_height = (9 if len(invoice.items) <= 10 else 7.5) * mm
    totals_height = (len(invoice.vat_per_rate()) + 3) * 6.5 * mm
    pages = paginate(invoice.items, row_height, totals_height)

    c = Canvas(str(out), pagesize=A4)
    c.setTitle(f"Invoice {invoice.number}")
    for index, items in enumerate(pages):
        y = first_page_header(c, invoice) if index == 0 else continued_header(c, invoice)
        if items:
            table_header(c, y)
            y -= 11 * mm
            for item in items:
                item_row(c, y, item, row_height)
                y -= row_height
        if index == len(pages) - 1:
            totals(c, y - 3 * mm, invoice)
            payment_block(c, invoice)
        page_footer(c, index + 1, len(pages))
        c.showPage()
    c.save()


def expected(invoice: Invoice) -> dict:
    """The values an extraction should find, in the field names of the app's analyzer."""
    return {
        "InvoiceNumber": invoice.number,
        "PurchaseOrder": invoice.purchase_order,
        "Subtotal": invoice.subtotal,
        "VatAmount": invoice.vat,
        "TotalAmount": invoice.total,
        "Currency": "EUR",
        "LineItems": [
            {
                "Description": item.description,
                "Quantity": item.quantity,
                "UnitPrice": item.unit_price,
                "VatRate": f"{item.vat_rate}%",
                "Amount": item.amount,
            }
            for item in invoice.items
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", type=int, help="generate this many line items instead of the fixed four")
    args = parser.parse_args()

    SAMPLES.mkdir(exist_ok=True)
    if args.items is None:
        out = SAMPLES / "invoice.pdf"
        draw(FIXED, out)
    else:
        invoice = generated(args.items)
        out = SAMPLES / f"invoice-{args.items}-items.pdf"
        draw(invoice, out)
        out.with_suffix(".json").write_text(json.dumps(expected(invoice), indent=1) + "\n")
    print(out)  # noqa: T201


if __name__ == "__main__":
    main()
