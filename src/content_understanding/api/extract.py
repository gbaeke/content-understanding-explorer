"""Upload a document, get its fields back with confidence and source regions."""

from pathlib import Path
from typing import Annotated

from azure.core.exceptions import AzureError
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..extraction import ANALYZER_ID, COMPLETION_MODEL, Extraction, render_pages, to_extraction
from .errors import ApiError

router = APIRouter()

SAMPLE = Path(__file__).resolve().parents[3] / "samples" / "invoice.pdf"
CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MAX_BYTES = 20 * 1024 * 1024


class Info(BaseModel):
    analyzer_id: str
    model: str  # the chat model the analyzer uses to fill the fields


@router.get("/info")
def info() -> Info:
    return Info(analyzer_id=ANALYZER_ID, model=COMPLETION_MODEL)


@router.get("/sample", response_class=FileResponse)
def sample() -> FileResponse:
    """The made-up invoice from scripts/make_sample_invoice.py, to try the app without a document of your own."""
    return FileResponse(SAMPLE, media_type="application/pdf", filename="invoice.pdf")


@router.post("/extract")
def extract(request: Request, file: Annotated[UploadFile, File()]) -> Extraction:
    # a plain `def`: the SDK call blocks for the whole analysis, so FastAPI runs it on a worker thread
    analyzer = request.app.state.analyzer
    if analyzer is None:
        raise ApiError("not_configured", "CONTENT_UNDERSTANDING_ENDPOINT is not set (see .env.example).", 503)
    content_type = file.content_type or ""
    if content_type not in CONTENT_TYPES:
        raise ApiError("unsupported_file", "Upload a PDF, PNG or JPEG file.", 415)
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError("file_too_large", "The file is larger than 20 MB.", 413)
    try:
        result = analyzer.analyze(data, content_type)
    except AzureError as exc:
        raise ApiError("extraction_failed", f"Content Understanding failed: {exc}", 502) from exc
    return to_extraction(result, render_pages(data, content_type))
