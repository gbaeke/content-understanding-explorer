from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import Settings, get_settings
from ..extraction import Analyzer, ContentUnderstanding
from ..middleware import RequestContext
from . import extract
from .errors import ApiError, install_handlers

ROOT = Path(__file__).resolve().parents[3]  # the repository (or /app in the image): alembic.ini, frontend/dist


def create_app(
    settings: Settings | None = None,
    analyzer: Analyzer | None = None,  # tests pass a fake; None: the real service, when an endpoint is set
) -> FastAPI:
    settings = settings or get_settings()
    if analyzer is None and settings.content_understanding_endpoint:
        analyzer = ContentUnderstanding(settings.content_understanding_endpoint)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(
        title="Content Understanding Explorer",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        lifespan=lifespan,
        # operation ids are the handlers' names: the generated client gets listNotes(), not listNotesApiNotesGet()
        generate_unique_id_function=lambda route: route.name,
    )
    app.state.settings = settings
    app.state.analyzer = analyzer
    install_handlers(app)
    app.add_middleware(RequestContext)  # added last, so it runs first: every response gets its id and headers

    api = APIRouter(prefix="/api")

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(extract.router)
    app.include_router(api)
    _serve_frontend(app, ROOT / "frontend" / "dist")
    return app


def _serve_frontend(app: FastAPI, dist: Path) -> None:
    """The built SPA: real files as they are, every other path gets index.html (the router takes it from there)."""
    if not dist.is_dir():
        return  # not built (tests, or `npm run dev` serves it)
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise ApiError("not_found", f"No API endpoint /{path}", 404)  # never the SPA for a mistyped API call
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist.resolve()):
            return FileResponse(file)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
