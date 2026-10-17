"""Same-origin authenticated ClauseGate API and static review workspace."""

import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from contracts.clausegate import (
    Assignment,
    ContextInput,
    DecisionInput,
    EgressInput,
    ErasureInput,
    Expected,
    FindingsInput,
    GrantInput,
    Login,
    Membership,
    Named,
    PlaybookInput,
    ReviewInput,
    Strict,
    TextInput,
    UserCreate,
)
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from clausegate_api.intake import pdf_document
from clausegate_api.reports import markdown
from clausegate_api.store import Store

COOKIE = "clausegate_session"


def create_app(*, store=None):
    store = store or Store(
        os.getenv("CLAUSEGATE_DATA_DIR", "var/clausegate"),
        ledger_dir=os.getenv("CLAUSEGATE_ERASURE_LEDGER_DIR"),
    )
    with store.connect() as db:
        empty = not db.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if empty:
        name, password = os.getenv("CLAUSEGATE_USERNAME"), os.getenv("CLAUSEGATE_PASSWORD")
        if not name or not password:
            raise RuntimeError("Set explicit ClauseGate bootstrap credentials")
        store.add_user(name, password, admin=True)
    app = FastAPI(title="ClauseGate", docs_url=None, redoc_url=None)
    app.state.store = store

    @app.exception_handler(PermissionError)
    def denied(request, error):
        return JSONResponse({"detail": str(error)}, status_code=403)

    @app.exception_handler(ValueError)
    @app.exception_handler(RuntimeError)
    def conflict(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.middleware("http")
    async def safety(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if origin and (
                urlsplit(origin).netloc != request.headers.get("host")
                or urlsplit(origin).scheme not in {"http", "https"}
            ):
                return JSONResponse({"detail": "Cross-origin mutation denied"}, status_code=403)
            body = bytearray()
            async for block in request.stream():
                body.extend(block)
                if len(body) > 20 * 1024**2:
                    return JSONResponse({"detail": "Request exceeds 20 MiB"}, status_code=413)
            request._body = bytes(body)
            if body and request.headers.get("content-type", "").split(";")[0] not in {
                "application/json",
                "application/pdf",
            }:
                return JSONResponse({"detail": "JSON or PDF required"}, status_code=415)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store" if request.url.path.startswith("/v1") else "no-cache",
                "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
            }
        )
        return response

    def actor(request: Request):
        try:
            value = store.authenticate(request.cookies.get(COOKIE, ""))
        except PermissionError as error:
            raise HTTPException(401, "Sign in required") from error
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
            value["csrf"], request.headers.get("X-CSRF-Token", "")
        ):
            raise HTTPException(403, "CSRF token required")
        return value["username"]

    @app.post("/v1/auth/session")
    def login(value: Login, response: Response):
        try:
            result = store.login(value.username, value.password)
        except PermissionError as error:
            raise HTTPException(401, str(error)) from error
        response.set_cookie(
            COOKIE,
            result.pop("token"),
            httponly=True,
            samesite="strict",
            secure=os.getenv("CLAUSEGATE_SECURE_COOKIES") == "1",
            max_age=28800,
            path="/",
        )
        return result

    @app.delete("/v1/auth/session")
    def logout(request: Request, response: Response, who=Depends(actor)):
        store.logout(request.cookies[COOKIE])
        response.delete_cookie(COOKIE, path="/")
        return {"status": "signed_out"}

    @app.get("/v1/me")
    def me(request: Request, who=Depends(actor)):
        return store.authenticate(request.cookies[COOKIE])

    @app.post("/v1/users")
    def user(value: UserCreate, who=Depends(actor)):
        if not store.user(who)["admin"]:
            raise PermissionError("Administrator required")
        store.add_user(value.username, value.password, value.admin)
        return {"username": value.username}

    @app.get("/v1/workspaces")
    def workspaces(who=Depends(actor)):
        return store.workspaces(who)

    @app.post("/v1/workspaces")
    def workspace(value: Named, who=Depends(actor)):
        return store.create_workspace(who, value.name)

    @app.get("/v1/workspaces/{wid}/members")
    def members(wid: str, who=Depends(actor)):
        return store.members(who, wid)

    @app.put("/v1/workspaces/{wid}/members")
    def membership(wid: str, value: Membership, who=Depends(actor)):
        store.membership(who, wid, value.username, value.roles, value.case_ids, value.expires_at)
        return {"status": "granted", "all_affected_contexts_staled": True}

    @app.post("/v1/workspaces/{wid}/cases")
    def new_case(wid: str, value: Named, who=Depends(actor)):
        return store.create_case(who, wid, value.name)

    @app.get("/v1/cases")
    def cases(who=Depends(actor)):
        return store.cases(who)

    @app.get("/v1/cases/{cid}")
    def case(cid: str, who=Depends(actor)):
        return store.case(who, cid)

    @app.put("/v1/cases/{cid}/context")
    def context(cid: str, value: ContextInput, who=Depends(actor)):
        return store.set_context(who, cid, value.expected_revision, value.side, value.purpose)

    @app.put("/v1/cases/{cid}/playbook")
    def playbook(cid: str, value: PlaybookInput, who=Depends(actor)):
        return store.set_playbook(who, cid, value.expected_revision, value.playbook)

    @app.put("/v1/cases/{cid}/playbook/draft")
    def draft(cid: str, value: PlaybookInput, who=Depends(actor)):
        return store.set_playbook(who, cid, value.expected_revision, value.playbook, activate=False)

    @app.put("/v1/cases/{cid}/egress")
    def egress(cid: str, value: EgressInput, who=Depends(actor)):
        return store.set_egress(who, cid, value.expected_revision, value.allowed)

    @app.post("/v1/cases/{cid}/imports")
    def imported(cid: str, value: TextInput, who=Depends(actor)):
        return store.import_text(who, cid, value.expected_revision, value.text, value.name)

    @app.post("/v1/cases/{cid}/documents")
    async def uploaded(
        cid: str,
        request: Request,
        expected_revision: int,
        name: str = "agreement.pdf",
        who=Depends(actor),
    ):
        if (
            not 1 <= len(name) <= 160
            or request.headers.get("content-type", "").split(";")[0] != "application/pdf"
        ):
            raise ValueError("PDF name/type required")
        # Authorize before parsing untrusted bytes; recheck in the write transaction.
        c = store.case(who, cid)
        if "requester" not in c["roles"]:
            raise PermissionError("Requester capability required")
        raw = await request.body()
        return store.import_document(who, cid, expected_revision, pdf_document(raw, name), raw)

    @app.get("/v1/documents/{did}")
    def document(did: str, who=Depends(actor)):
        return store.document(who, did)

    @app.get("/v1/documents/{did}/file")
    def original(did: str, who=Depends(actor)):
        return Response(
            content=store.original(who, did),
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="agreement-source.bin"'},
        )

    @app.post("/v1/cases/{cid}/analyses")
    def analysis(cid: str, value: GrantInput, who=Depends(actor)):
        return store.enqueue(who, cid, value.expected_revision, value.key)

    @app.get("/v1/cases/{cid}/jobs")
    def jobs(cid: str, who=Depends(actor)):
        return store.jobs(who, cid)

    @app.get("/v1/jobs/{jid}")
    def job(jid: str, who=Depends(actor)):
        with store.connect() as db:
            row = db.execute("SELECT case_id FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            raise PermissionError("Job access denied")
        return next(j for j in store.jobs(who, row[0]) if j["id"] == jid)

    @app.post("/v1/cases/{cid}/findings")
    def findings(cid: str, value: FindingsInput, who=Depends(actor)):
        return store.submit_findings(
            who, cid, value.expected_revision, value.findings, value.rationale
        )

    @app.get("/v1/approval-requests")
    def inbox(who=Depends(actor)):
        return store.inbox(who)

    @app.post("/v1/approval-requests/{rid}/decisions")
    def decision(rid: str, value: DecisionInput, who=Depends(actor)):
        return store.decide(who, rid, value)

    @app.put("/v1/approval-requests/{rid}/assignment")
    def assignment(rid: str, value: Assignment, who=Depends(actor)):
        return store.assign(who, rid, value.expected_revision, value.username, value.expires_at)

    @app.post("/v1/cases/{cid}/decisions/{did}/withdraw")
    def withdraw(cid: str, did: str, value: Expected, who=Depends(actor)):
        return store.withdraw(who, cid, did, value.expected_revision)

    @app.post("/v1/cases/{cid}/resume")
    def resume(cid: str, value: Strict, who=Depends(actor)):
        return store.resume(who, cid)

    @app.post("/v1/cases/{cid}/cancel")
    def cancel(cid: str, value: Expected, who=Depends(actor)):
        return store.cancel(who, cid, value.expected_revision)

    @app.post("/v1/cases/{cid}/reviews")
    def review(cid: str, value: ReviewInput, who=Depends(actor)):
        return store.finalize(
            who,
            cid,
            value.expected_revision,
            value.packet_hash,
            value.rationale,
            value.acknowledge_limits,
        )

    @app.get("/v1/cases/{cid}/export")
    def export(cid: str, format: str = "json", who=Depends(actor)):
        payload = store.export(who, cid)
        if format == "markdown":
            return PlainTextResponse(
                markdown(payload),
                headers={
                    "Content-Disposition": 'attachment; filename="clausegate-internal-review.md"'
                },
            )
        if format != "json":
            raise ValueError("JSON or Markdown export required")
        return payload

    @app.get("/v1/cases/{cid}/audit")
    def audit(cid: str, offset: int = 0, limit: int = 100, who=Depends(actor)):
        return store.audit(who, cid, offset, limit)

    @app.post("/v1/cases/{cid}/audit/anchor")
    def anchor(cid: str, value: Strict, who=Depends(actor)):
        return store.anchor(who, cid)

    @app.get("/v1/cases/{cid}/erasures/preview")
    def preview(cid: str, who=Depends(actor)):
        return store.erase_preview(who, cid)

    @app.post("/v1/cases/{cid}/erasures")
    def erase(cid: str, value: ErasureInput, who=Depends(actor)):
        return store.erase(who, cid, value.expected_revision, value.confirmation)

    @app.get("/health/live")
    def live():
        return {"status": "live"}

    @app.get("/health/ready")
    def ready():
        if store.setting("quarantined"):
            return JSONResponse({"status": "quarantined"}, status_code=503)
        return {"status": "ready", "generation": "explicit-egress-and-installed-runtime-required"}

    dist = Path(__file__).resolve().parents[3] / "clausegate-web" / "dist"

    @app.get("/")
    def index():
        if not (dist / "index.html").is_file():
            return PlainTextResponse("Build ClauseGate web first", status_code=503)
        return FileResponse(dist / "index.html")

    @app.get("/assets/{name}")
    def assets(name: str):
        path = (dist / "assets" / name).resolve()
        if path.parent != (dist / "assets").resolve() or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    return app


def app_from_env():
    return create_app()
