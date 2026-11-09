"""Invoice extraction with Azure Content Understanding: the analyzer definition, the call, and the result in the
shape the viewer needs (fields with a confidence and the regions on the page they came from)."""

import base64
import re
from io import BytesIO
from typing import Any, Protocol

import pypdfium2
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel

ANALYZER_ID = "invoice_explorer"
COMPLETION_MODEL = "gpt-6.1-sol"  # model names, as Content Understanding knows them; infra/main.bicep deploys both
EMBEDDING_MODEL = "text-embedding-3-large"  # under the same name
MAX_PAGES = 10
RENDER_SCALE = 2  # PDF points to pixels: 144 dpi, sharp enough to read and small enough to send inline


def _field(kind: str, description: str) -> dict[str, Any]:
    """A field taken literally from the page ("extract"), with its confidence and source location."""
    return {"type": kind, "method": "extract", "description": description, "estimateSourceAndConfidence": True}


# The one definition of what is extracted: section title -> field name -> schema. The analyzer's field schema and
# the grouping in the viewer both come from this. An array of objects is shown as a table.
SECTIONS: dict[str, dict[str, dict[str, Any]]] = {
    "Header": {
        "VendorName": _field("string", "Name of the company that issued the invoice (the seller)."),
        "VendorAddress": _field("string", "Full postal address of the seller."),
        "VendorVatNumber": _field("string", "VAT number of the seller, as printed."),
        "CustomerName": _field("string", "Name of the company or person the invoice is addressed to (the buyer)."),
        "CustomerAddress": _field("string", "Full postal address of the buyer."),
        "CustomerVatNumber": _field("string", "VAT number of the buyer, as printed."),
        "InvoiceNumber": _field("string", "The invoice number."),
        "InvoiceDate": _field("date", "Date the invoice was issued."),
        "DueDate": _field("date", "Date the payment is due."),
        "PurchaseOrder": _field("string", "Purchase order number or other reference of the buyer."),
    },
    "Line items": {
        "LineItems": {
            "type": "array",
            "description": "Every line of the invoice table: one item per product or service billed.",
            "items": {
                "type": "object",
                "properties": {
                    "Description": _field("string", "What was sold."),
                    "Quantity": _field("number", "Number of units."),
                    "UnitPrice": _field("number", "Price of one unit, without VAT."),
                    "VatRate": _field("string", "VAT rate of this line, as printed (for example 21%)."),
                    "Amount": _field("number", "Total of this line, without VAT."),
                },
            },
        },
    },
    "Totals": {
        "Subtotal": _field("number", "Sum of all lines before VAT."),
        "VatAmount": _field("number", "Total VAT amount."),
        "TotalAmount": _field("number", "Total amount to pay, VAT included."),
        "Currency": _field("string", "Currency of the amounts, as an ISO 4217 code when printed (for example EUR)."),
    },
    "Footer": {
        "Iban": _field("string", "IBAN of the bank account to pay to."),
        "Bic": _field("string", "BIC or SWIFT code of the seller's bank."),
        "PaymentReference": _field("string", "Reference to mention with the payment (structured communication)."),
        "PaymentTerms": _field("string", "The payment terms: when and how to pay, penalties for late payment."),
    },
}

ANALYZER: dict[str, Any] = {
    "description": "Invoice header, line items, totals and payment footer, with confidence and source location",
    "baseAnalyzerId": "prebuilt-document",
    "models": {"completion": COMPLETION_MODEL, "embedding": EMBEDDING_MODEL},
    "config": {"returnDetails": True, "estimateFieldSourceAndConfidence": True},
    "fieldSchema": {
        "name": "Invoice",
        "fields": {name: schema for fields in SECTIONS.values() for name, schema in fields.items()},
    },
}


class Region(BaseModel):
    """Where a value was found: a four-corner polygon [x1, y1, ... x4, y4] in the units of that page."""

    page: int
    polygon: list[float]


class Field(BaseModel):
    id: str  # unique in the result: "InvoiceNumber", "LineItems[2].Amount"
    name: str
    type: str
    value: str | float | bool | None
    confidence: float | None  # 0 to 1; None when the service gave none
    regions: list[Region]


class Table(BaseModel):
    columns: list[str]
    rows: list[list[Field]]  # one Field per column, in column order


class Section(BaseModel):
    """A group of values, in the order of SECTIONS: plain fields, or a table for an array of objects."""

    title: str
    fields: list[Field]
    table: Table | None


class Page(BaseModel):
    number: int
    width: float  # in the units the polygons use (inches for a PDF, pixels for an image)
    height: float
    image: str  # data URL


class Extraction(BaseModel):
    pages: list[Page]
    sections: list[Section]


class Analyzer(Protocol):
    def analyze(self, data: bytes, content_type: str) -> dict[str, Any]:
        """The service's analysis result as a plain dict (REST casing)."""
        ...


class ContentUnderstanding:
    """The real service. Signs in with the developer's Azure login (or a managed identity), no keys."""

    def __init__(self, endpoint: str):
        self._client = ContentUnderstandingClient(endpoint, DefaultAzureCredential())
        self._ready = False

    def _prepare(self) -> None:
        """Once per process: tell the resource which deployments to use, and (re)create our analyzer so a change
        to SECTIONS takes effect on the next start."""
        self._client.update_defaults(
            model_deployments={COMPLETION_MODEL: COMPLETION_MODEL, EMBEDDING_MODEL: EMBEDDING_MODEL}
        )
        self._client.begin_create_analyzer(ANALYZER_ID, ANALYZER, allow_replace=True).result()
        self._ready = True

    def analyze(self, data: bytes, content_type: str) -> dict[str, Any]:
        if not self._ready:
            self._prepare()
        poller = self._client.begin_analyze_binary(ANALYZER_ID, data, content_type=content_type)
        return poller.result().as_dict()


def render_pages(data: bytes, content_type: str) -> list[str]:
    """One data URL per page: a PDF is rendered, an image is its own single page."""
    if content_type != "application/pdf":
        return [f"data:{content_type};base64,{base64.b64encode(data).decode()}"]
    images: list[str] = []
    pdf = pypdfium2.PdfDocument(data)
    try:
        for index in range(min(len(pdf), MAX_PAGES)):
            bitmap = pdf[index].render(scale=RENDER_SCALE)
            # PNG via pillow: lossless, so text stays crisp under the highlight
            buffer = BytesIO()
            bitmap.to_pil().save(buffer, format="PNG", optimize=True)
            images.append(f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}")
    finally:
        pdf.close()
    return images


_SOURCE = re.compile(r"D\((\d+),([^)]*)\)")


def _regions(source: str | None) -> list[Region]:
    """ "D(1,0.5,1.2,...);D(2,...)" -> regions. The service joins several places with a semicolon."""
    regions: list[Region] = []
    for page, numbers in _SOURCE.findall(source or ""):
        polygon = [float(n) for n in numbers.split(",")]
        if len(polygon) == 8:
            regions.append(Region(page=int(page), polygon=polygon))
    return regions


def _to_field(field_id: str, name: str, raw: dict[str, Any] | None) -> Field:
    raw = raw or {}
    kind = raw.get("type", "string")
    value = next((v for k, v in raw.items() if k.startswith("value")), None)
    if isinstance(value, (dict, list)):
        value = None  # nested values are flattened by the caller, never shown as one cell
    return Field(
        id=field_id,
        name=name,
        type=kind,
        value=value,
        confidence=raw.get("confidence"),
        regions=_regions(raw.get("source")),
    )


def to_extraction(result: dict[str, Any], images: list[str]) -> Extraction:
    """The service's result plus the page images, grouped the way SECTIONS says."""
    content = (result.get("contents") or [{}])[0]
    raw_fields: dict[str, Any] = content.get("fields") or {}
    pages = [
        Page(number=p["pageNumber"], width=p["width"], height=p["height"], image=image)
        for p, image in zip(content.get("pages") or [], images, strict=False)
    ]

    sections: list[Section] = []
    for title, fields in SECTIONS.items():
        plain: list[Field] = []
        table: Table | None = None
        for name, schema in fields.items():
            raw = raw_fields.get(name)
            if schema["type"] != "array":
                plain.append(_to_field(name, name, raw))
                continue
            columns = list(schema["items"]["properties"])
            rows = [
                [
                    _to_field(f"{name}[{index}].{column}", column, (item.get("valueObject") or {}).get(column))
                    for column in columns
                ]
                for index, item in enumerate((raw or {}).get("valueArray") or [])
            ]
            table = Table(columns=columns, rows=rows)
        sections.append(Section(title=title, fields=plain, table=table))
    return Extraction(pages=pages, sections=sections)
