import json
from pathlib import Path

import pytest
from azure.core.exceptions import HttpResponseError
from fastapi.testclient import TestClient

from content_understanding.api.app import create_app
from content_understanding.extraction import ANALYZER_ID, COMPLETION_MODEL

DATA = Path(__file__).parent / "data"
SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "invoice.pdf"


class FakeAnalyzer:
    """Answers with a result recorded from the real service for samples/invoice.pdf (trimmed to fields and pages)."""

    def __init__(self, fail: Exception | None = None):
        self.fail = fail
        self.calls: list[tuple[int, str]] = []

    def analyze(self, data: bytes, content_type: str) -> dict:
        self.calls.append((len(data), content_type))
        if self.fail:
            raise self.fail
        return json.loads((DATA / "invoice_result.json").read_text())


@pytest.fixture
def analyzer():
    return FakeAnalyzer()


@pytest.fixture
def client(settings, analyzer):
    with TestClient(create_app(settings, analyzer)) as c:
        yield c


def upload(client, content_type="application/pdf"):
    return client.post("/api/extract", files={"file": ("invoice.pdf", SAMPLE.read_bytes(), content_type)})


def test_extract_groups_fields_with_confidence_and_regions(client, analyzer):
    res = upload(client)
    assert res.status_code == 200
    body = res.json()
    assert analyzer.calls == [(SAMPLE.stat().st_size, "application/pdf")]

    assert [s["title"] for s in body["sections"]] == ["Header", "Line items", "Totals", "Footer"]
    header = {f["name"]: f for f in body["sections"][0]["fields"]}
    assert header["InvoiceNumber"]["value"] == "2026-0147"
    assert header["InvoiceDate"]["value"] == "2026-11-03"  # the service normalizes dates
    assert 0.9 < header["InvoiceNumber"]["confidence"] <= 1
    region = header["InvoiceNumber"]["regions"][0]
    assert region["page"] == 1
    assert len(region["polygon"]) == 8
    assert len(header["VendorAddress"]["regions"]) == 2  # a value on two lines has two regions


def test_extract_turns_the_line_items_into_a_table(client):
    section = upload(client).json()["sections"][1]
    assert section["fields"] == []
    table = section["table"]
    assert table["columns"] == ["Description", "Quantity", "UnitPrice", "VatRate", "Amount"]
    assert len(table["rows"]) == 4
    first = table["rows"][0]
    assert [cell["value"] for cell in first] == ["Azure architecture workshop (per day)", 2, 1250, "21%", 2500]
    assert first[4]["id"] == "LineItems[0].Amount"
    assert first[4]["regions"]


def test_extract_returns_one_image_per_page_in_the_units_of_the_regions(client):
    pages = upload(client).json()["pages"]
    assert len(pages) == 1
    assert pages[0]["image"].startswith("data:image/png;base64,")
    assert pages[0]["width"] == pytest.approx(8.26, abs=0.01)  # A4 in inches, like the polygons


def test_extract_refuses_other_file_types(client, analyzer):
    res = upload(client, content_type="text/plain")
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "unsupported_file"
    assert analyzer.calls == []


def test_a_service_failure_is_a_502_in_the_error_envelope(settings):
    with TestClient(create_app(settings, FakeAnalyzer(fail=HttpResponseError("quota exceeded")))) as client:
        res = upload(client)
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "extraction_failed"


def test_without_an_endpoint_extraction_is_not_configured(settings):
    with TestClient(create_app(settings)) as client:
        res = upload(client)
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "not_configured"


def test_sample_is_the_invoice_pdf(client):
    res = client.get("/api/sample")
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")


def test_info_names_the_model_the_analyzer_uses(client):
    assert client.get("/api/info").json() == {"analyzer_id": ANALYZER_ID, "model": COMPLETION_MODEL}
