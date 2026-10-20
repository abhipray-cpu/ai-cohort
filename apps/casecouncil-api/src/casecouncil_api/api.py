"""Scoped same-origin review API. No remote source acquisition or automatic customer actions."""

import html
import os
import secrets
import sqlite3
import time
from pathlib import Path

from contracts.casecouncil import Context, Policy, Review, Rights, Strict
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from . import journal
from .consensus import canonical
from .store import Store


class Credentials(Strict):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=1000)


class WorkspaceSpec(Strict):
    name: str = Field(min_length=3, max_length=150)


class Member(Strict):
    username: str = Field(min_length=1, max_length=100)
    role: str | None = Field(pattern=r"^(owner|analyst|reviewer|viewer)$")


class CaseSpec(Strict):
    workspace: str = Field(min_length=1, max_length=100)
    context: Context


class ContextEdit(Strict):
    revision: int = Field(ge=1)
    context: Context


class PolicyEdit(Strict):
    revision: int = Field(ge=1)
    policy: Policy


class Start(Strict):
    binding: str = Field(min_length=64, max_length=64)


class Erasure(Strict):
    revision: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=2000)


def create_app(data_dir, *, username, password, secure=False, evaluation_only=False):
    if not username or len(password) < 12 or password == "replace-me":
        raise ValueError("explicit service credentials required")
    store = Store(data_dir, evaluation_only=evaluation_only)
    store.bootstrap(username, password)
    app = FastAPI(title="CaseCouncil", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    failures = {}

    @app.middleware("http")
    async def boundary(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > 11 * 1024 * 1024:
                    return JSONResponse({"detail": "request limit"}, 413)
            request._body = bytes(data)
        if request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if (
                request.method not in {"GET", "HEAD"}
                and origin
                and origin != str(request.base_url).rstrip("/")
            ):
                return JSONResponse({"detail": "origin denied"}, 403)
            if request.url.path != "/api/session":
                actor = store.session(request.cookies.get("casecouncil_session", ""))
                if not actor:
                    return JSONResponse({"detail": "authentication required"}, 401)
                request.state.actor = actor
                if request.method not in {"GET", "HEAD"} and not secrets.compare_digest(
                    request.headers.get("X-CSRF-Token", "").encode(), actor["csrf"].encode()
                ):
                    return JSONResponse({"detail": "CSRF check failed"}, 403)
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            }
        )
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "not found"}, 404)

    @app.exception_handler(PermissionError)
    async def forbidden(request, exc):
        return JSONResponse({"detail": "capability or source authority denied"}, 403)

    @app.exception_handler(ValueError)
    async def conflict(request, exc):
        return JSONResponse(
            {"detail": "operation conflicts with source, rights, revision, or resource policy"}, 409
        )

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity(request, exc):
        return JSONResponse({"detail": "invalid or duplicate reference"}, 409)

    @app.exception_handler(RequestValidationError)
    async def bad_input(request, exc):
        return JSONResponse(
            {
                "detail": "invalid bounded input",
                "fields": [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
            },
            422,
        )

    def who(request):
        return request.state.actor["name"]

    def key(request):
        value = request.headers.get("Idempotency-Key", "")
        if not value or len(value) > 150:
            raise HTTPException(422, "Idempotency-Key required")
        return value

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        with store.connect() as db:
            meta = db.execute("SELECT schema_version FROM meta WHERE id=1").fetchone()
            beat = db.execute("SELECT updated FROM heartbeat WHERE id='worker'").fetchone()
        ok = bool(meta and meta[0] == 2 and beat and time.time() - beat[0] < 60)
        try:
            with store.connect() as db:
                journal.assert_current(db, store.journal_path)
        except (ValueError, OSError):
            ok = False
        return JSONResponse({"ready": ok, "model_connection_verified": False}, 200 if ok else 503)

    @app.post("/api/session")
    def login(body: Credentials, request: Request):
        addr = request.client.host if request.client else "unknown"
        now = time.time()
        attempts = [t for t in failures.get(addr, []) if now - t < 60]
        if len(attempts) >= 8:
            raise HTTPException(429, "too many attempts")
        try:
            value = store.login(body.username, body.password)
        except PermissionError:
            if len(failures) > 10000:
                failures.clear()
            failures[addr] = attempts + [now]
            raise HTTPException(401, "invalid credentials") from None
        failures.pop(addr, None)
        response = JSONResponse({"name": value["name"], "csrf": value["csrf"]})
        response.set_cookie(
            "casecouncil_session",
            value["token"],
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=8 * 3600,
        )
        return response

    @app.delete("/api/session")
    def logout(request: Request):
        actor = store.session(request.cookies.get("casecouncil_session", ""))
        if not actor or not secrets.compare_digest(
            request.headers.get("X-CSRF-Token", "").encode(), actor["csrf"].encode()
        ):
            raise HTTPException(403, "CSRF denied")
        store.logout(request.cookies.get("casecouncil_session", ""))
        r = Response(status_code=204)
        r.delete_cookie("casecouncil_session")
        return r

    @app.get("/api/me")
    def me(request: Request):
        return {**request.state.actor, "workspaces": store.workspaces(who(request))}

    @app.post("/api/users", status_code=201)
    def user(body: Credentials, request: Request):
        store.add_user(who(request), body.username, body.password)
        return {"name": body.username}

    @app.get("/api/workspaces")
    def workspaces(request: Request):
        return store.workspaces(who(request))

    @app.post("/api/workspaces", status_code=201)
    def workspace(body: WorkspaceSpec, request: Request):
        return {"id": store.create_workspace(who(request), body.name, key(request))}

    @app.get("/api/workspaces/{wid}")
    def workspace_detail(wid: str, request: Request):
        return store.workspace(who(request), wid)

    @app.get("/api/workspaces/{wid}/members")
    def members(wid: str, request: Request):
        return store.members(who(request), wid)

    @app.put("/api/workspaces/{wid}/members")
    def member(wid: str, body: Member, request: Request):
        def change():
            store.set_member(who(request), wid, body.username, body.role)
            return {"updated": True}

        return store.admin_action(
            who(request), wid, "member", key(request), body.model_dump(), change
        )

    @app.put("/api/workspaces/{wid}/policy")
    def policy(wid: str, body: PolicyEdit, request: Request):
        def change():
            store.set_policy(who(request), wid, body.revision, body.policy.model_dump())
            return {"updated": True}

        return store.admin_action(
            who(request), wid, "policy", key(request), body.model_dump(), change
        )

    @app.get("/api/workspaces/{wid}/rights")
    def rights(wid: str, request: Request):
        return store.rights(who(request), wid)

    @app.post("/api/workspaces/{wid}/rights", status_code=201)
    def clearance(wid: str, body: Rights, request: Request):
        return store.admin_action(
            who(request),
            wid,
            "rights",
            key(request),
            body.model_dump(),
            lambda: {"id": store.add_rights(who(request), wid, body.model_dump())},
        )

    @app.delete("/api/workspaces/{wid}/rights/{rid}")
    def revoke(wid: str, rid: str, request: Request):
        def change():
            store.revoke_rights(who(request), wid, rid)
            return {"revoked": True}

        return store.admin_action(
            who(request), wid, "revoke-rights", key(request), {"id": rid}, change
        )

    @app.get("/api/workspaces/{wid}/cases")
    def cases(wid: str, request: Request):
        return store.cases(who(request), wid)

    @app.post("/api/cases", status_code=201)
    def case(body: CaseSpec, request: Request):
        return store.create_case(
            who(request), body.workspace, body.context.model_dump(), key(request)
        )

    @app.get("/api/cases/{cid}")
    def detail(cid: str, request: Request):
        return store.case(who(request), cid)

    @app.put("/api/cases/{cid}")
    def edit(cid: str, body: ContextEdit, request: Request):
        return store.update_case(
            who(request), cid, body.revision, body.context.model_dump(), key(request)
        )

    @app.post("/api/cases/{cid}/sources", status_code=201)
    async def upload(
        cid: str,
        request: Request,
        revision: int = Form(...),
        kind: str = Form(...),
        rights_id: str = Form(...),
        replaces: str | None = Form(None),
        file: UploadFile = File(...),
    ):
        store.case(who(request), cid)
        raw = await file.read(10 * 1024 * 1024 + 1)
        return store.add_source(
            who(request),
            cid,
            revision,
            file.filename or "",
            raw,
            kind,
            rights_id,
            key(request),
            replaces,
        )

    @app.get("/api/sources/{sid}")
    def source(sid: str, request: Request):
        return store.source(who(request), sid)

    @app.get("/api/cases/{cid}/egress-preview")
    def preview(cid: str, request: Request):
        value = store.preview(who(request), cid)
        # No unselected source body is represented as approved model input.
        return {
            **value,
            "evidence": {k: v for k, v in value["evidence"].items() if k != "sources"},
            "limits": {"max_calls": 22, "active_seconds": 1800, "remote_inference_possible": True},
        }

    @app.post("/api/cases/{cid}/runs", status_code=202)
    def run(cid: str, body: Start, request: Request):
        return store.start(who(request), cid, body.binding, key(request))

    @app.get("/api/cases/{cid}/runs")
    def runs(cid: str, request: Request):
        return store.list_jobs(who(request), cid)

    @app.get("/api/runs/{jid}")
    def run_detail(jid: str, request: Request):
        return store.job(who(request), jid)

    @app.post("/api/runs/{jid}/cancel")
    def cancel(jid: str, request: Request):
        store.cancel(who(request), jid)
        return {"cancelled": True}

    @app.post("/api/runs/{jid}/reviews", status_code=201)
    def review(jid: str, body: Review, request: Request):
        return store.review(who(request), jid, body.model_dump(), key(request))

    @app.get("/api/runs/{jid}/export")
    def export(jid: str, request: Request, reviewed: bool = False, format: str = "json"):
        value = store.export(who(request), jid, reviewed)
        if format == "html":
            return HTMLResponse(
                "<!doctype html><html lang=en><meta charset=utf-8><title>CaseCouncil review export</title><h1>"
                + html.escape(value["label"])
                + "</h1><p>Advisory record, not a binding decision. Verify source currency before use.</p><pre>"
                + html.escape(canonical(value))
                + "</pre></html>",
                headers={"Content-Disposition": f'attachment; filename="casecouncil-{jid}.html"'},
            )
        if format != "json":
            raise HTTPException(422, "unsupported export")
        return JSONResponse(
            value, headers={"Content-Disposition": f'attachment; filename="casecouncil-{jid}.json"'}
        )

    @app.get("/api/workspaces/{wid}/audit")
    def audit(wid: str, request: Request, after: int = 0):
        return store.audit(who(request), wid, max(0, after))

    @app.get("/api/cases/{cid}/erasure-preview")
    def erasure(cid: str, request: Request):
        return store.erasure_preview(who(request), cid)

    @app.delete("/api/cases/{cid}")
    def erase(cid: str, body: Erasure, request: Request):
        store.erase(who(request), cid, body.revision, body.reason)
        return {"erased": True}

    dist = Path(__file__).resolve().parents[3] / "casecouncil-web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


def app_from_env():
    return create_app(
        os.environ.get("CASECOUNCIL_DATA_DIR", "var/casecouncil"),
        username=os.environ.get("CASECOUNCIL_USERNAME", ""),
        password=os.environ.get("CASECOUNCIL_PASSWORD", ""),
        secure=os.environ.get("CASECOUNCIL_SECURE_COOKIES", "").lower() == "true",
    )
