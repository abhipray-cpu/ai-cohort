"""Authenticated ResolveDesk API and same-origin reviewer web host."""

import os
import secrets
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from contracts.resolvedesk import CaseInput, ChatCreate, ChatMessage, ReviewAction, SourceInput
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from resolvedesk_api.ingest import parse_document_details
from resolvedesk_api.network import approved_url, fetch_page, make_search
from resolvedesk_api.store import Store


class EnvironmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    changes: dict[str, str | None] = Field(max_length=3)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["json", "markdown"] = "json"
    escalation: bool = False


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    urls: list[str] = Field(min_length=1, max_length=5)


def create_app(*, data_dir=None, username=None, password=None):
    username = username or os.getenv("RESOLVEDESK_USERNAME")
    password = password or os.getenv("RESOLVEDESK_PASSWORD")
    if not username or not password or password == "replace-me":
        raise RuntimeError("Configure RESOLVEDESK_USERNAME and RESOLVEDESK_PASSWORD")
    store = Store(data_dir or os.getenv("RESOLVEDESK_DATA_DIR", "var/resolvedesk"))
    app = FastAPI(title="ResolveDesk", version="0.1.0")
    app.state.store = store
    security = HTTPBasic()

    def authorize(credentials: HTTPBasicCredentials = Depends(security)):
        if not (
            secrets.compare_digest(credentials.username.encode(), username.encode())
            and secrets.compare_digest(credentials.password.encode(), password.encode())
        ):
            raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Basic"})
        return credentials.username

    @app.middleware("http")
    async def headers(request, call_next):
        origin = request.headers.get("origin")
        try:
            origin_host = urlsplit(origin).netloc if origin else None
        except ValueError:
            origin_host = ""
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin_host != request.headers.get("host")
        ):
            return JSONResponse(
                {"detail": "Cross-origin changes are not permitted"}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    def conflict(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/health/live")
    def live():
        return {"status": "ok", "product": "resolvedesk"}

    @app.get("/health/ready")
    def ready():
        store.connect().close()
        return {"status": "ok", "product": "resolvedesk"}

    @app.get("/v1/settings", dependencies=[Depends(authorize)])
    def settings():
        return {
            "search_configured": make_search().configured,
            "search_provider": os.getenv("RESOLVEDESK_SEARCH_PROVIDER", "postgresql"),
            "supported_versions": ["16", "17"],
            "index_revision": store.index_revision(),
            "retrieval": "SQLite FTS5 BM25",
            "generation": "Installed Codex CLI",
        }

    @app.get("/v1/cases", dependencies=[Depends(authorize)])
    def cases():
        return store.cases()

    @app.get("/v1/chats", dependencies=[Depends(authorize)])
    def chats():
        return store.chats()

    @app.post("/v1/chats", status_code=201)
    def create_chat(value: ChatCreate, actor=Depends(authorize)):
        return store.create_chat(value, actor)

    @app.get("/v1/chats/{cid}", dependencies=[Depends(authorize)])
    def chat(cid: str):
        result = store.chat(cid)
        if not result:
            raise HTTPException(404, "Conversation not found")
        return result

    @app.post("/v1/chats/{cid}/messages", status_code=202)
    def send_message(
        cid: str,
        value: ChatMessage,
        actor=Depends(authorize),
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        return conflict(store.send_message, cid, value, idempotency_key, actor)

    @app.post("/v1/cases", status_code=201)
    def create_case(value: CaseInput, actor=Depends(authorize)):
        return store.create_case(value, actor)

    @app.get("/v1/cases/{cid}", dependencies=[Depends(authorize)])
    def case(cid: str):
        value = store.case(cid)
        if not value:
            raise HTTPException(404, "Case not found")
        return {**value, "latest_run": store.latest_run(cid)}

    @app.patch("/v1/cases/{cid}/environment")
    def environment(cid: str, value: EnvironmentUpdate, actor=Depends(authorize)):
        return conflict(
            store.update_environment, cid, value.expected_revision, value.changes, actor
        )

    @app.post("/v1/cases/{cid}/runs", status_code=202, dependencies=[Depends(authorize)])
    def create_run(cid: str, idempotency_key: str = Header(alias="Idempotency-Key")):
        return conflict(store.create_run, cid, idempotency_key)

    @app.get("/v1/runs/{rid}", dependencies=[Depends(authorize)])
    def run(rid: str):
        value = store.run(rid)
        if not value:
            raise HTTPException(404, "Investigation not found")
        return value

    @app.post("/v1/runs/{rid}/retry", status_code=202, dependencies=[Depends(authorize)])
    def retry(rid: str):
        conflict(store.retry, rid)
        return store.run(rid)

    @app.get("/v1/answers/{aid}", dependencies=[Depends(authorize)])
    def answer(aid: str):
        value = store.answer(aid)
        if not value:
            raise HTTPException(404, "Answer not found")
        return value

    @app.patch("/v1/answers/{aid}/review")
    def review(aid: str, value: ReviewAction, actor=Depends(authorize)):
        return conflict(
            store.review,
            aid,
            value.expected_revision,
            value.action,
            value.reason,
            actor,
            claim_texts=value.claim_texts,
            acknowledge_limits=value.acknowledge_limits,
            allow_internal=value.allow_internal,
        )

    @app.post("/v1/answers/{aid}/exports", dependencies=[Depends(authorize)])
    def export(aid: str, value: ExportRequest):
        result = conflict(store.export, aid, value.format, escalation=value.escalation)
        return (
            PlainTextResponse(result, media_type="text/markdown")
            if value.format == "markdown"
            else result
        )

    @app.get("/v1/sources", dependencies=[Depends(authorize)])
    def sources():
        return store.sources()

    @app.post("/v1/sources", status_code=201, dependencies=[Depends(authorize)])
    def import_source(value: SourceInput):
        if value.visibility != "internal":
            raise HTTPException(
                422, "Manual runbooks must be internal; fetch official sources separately"
            )
        return store.import_source(
            title=value.title,
            url="internal:" + secrets.token_hex(12),
            text=value.text,
            version=value.version,
            visibility="internal",
        )

    @app.get("/v1/sources/{sid}", dependencies=[Depends(authorize)])
    def source(sid: str):
        value = store.source(sid)
        if not value:
            raise HTTPException(404, "Source not found")
        return {**value, "passages": store.source_passages(sid)}

    @app.post("/v1/sources/{sid}/promote", dependencies=[Depends(authorize)])
    def promote(sid: str):
        return conflict(store.promote_source, sid)

    @app.post("/v1/sources/refresh", dependencies=[Depends(authorize)])
    def refresh(value: RefreshRequest):
        import re

        results = []
        for raw_url in value.urls:
            try:
                url = approved_url(raw_url)
                text, sections = parse_document_details(fetch_page(url))
                version = re.search(r"/docs/(16|17)/", url).group(1)
                source = store.import_source(
                    title=url.rsplit("/", 1)[-1],
                    url=url,
                    version=version,
                    text=text,
                    sections=sections,
                )
                results.append({"url": url, "status": "ready", "snapshot_id": source["id"]})
            except (ValueError, RuntimeError, OSError):
                results.append(
                    {
                        "url": raw_url,
                        "status": "failed",
                        "error": "Source could not be fetched or validated",
                    }
                )
        return {"results": results, "index_revision": store.index_revision()}

    dist = Path(__file__).resolve().parents[3] / "resolvedesk-web" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", dependencies=[Depends(authorize)])
        def index():
            return FileResponse(dist / "index.html")

    return app


def app_from_env():
    return create_app()
