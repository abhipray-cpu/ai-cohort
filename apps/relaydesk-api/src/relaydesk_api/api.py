"""Same-origin session/CSRF API and static RelayDesk application."""

import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from contracts.relaydesk import (
    Correction,
    Erasure,
    ExpectedRevision,
    GithubInput,
    ImportBatch,
    Login,
    Membership,
    Message,
    Named,
    Policy,
    Recall,
    Review,
    UserCreate,
)
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from relaydesk_api.context import compress
from relaydesk_api.ingest import GithubSources
from relaydesk_api.store import Store

COOKIE = "relaydesk_session"


def create_app(*, store=None, data_dir=None, sources=None):
    store = store or Store(
        data_dir or os.getenv("RELAYDESK_DATA_DIR", "var/relaydesk"),
        ledger_dir=os.getenv("RELAYDESK_ERASURE_LEDGER_DIR"),
    )
    with store.connect() as db:
        empty = not db.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if empty:
        username, password = os.getenv("RELAYDESK_USERNAME"), os.getenv("RELAYDESK_PASSWORD")
        if not username or not password:
            raise RuntimeError("Set explicit RelayDesk bootstrap credentials")
        store.add_user(username, password, admin=True)
    app = FastAPI(title="RelayDesk", docs_url=None, redoc_url=None)
    app.state.store = store

    def checked(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PermissionError as error:
            raise HTTPException(403, str(error)) from error
        except (ValueError, RuntimeError) as error:
            raise HTTPException(409, str(error)) from error
        except (OSError, TimeoutError) as error:
            raise HTTPException(502, "Source unavailable; no synthetic substitute") from error

    def actor(request: Request):
        try:
            identity = store.authenticate(request.cookies.get(COOKIE, ""))
        except PermissionError as error:
            raise HTTPException(401, "Sign in required") from error
        if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
            identity["csrf"], request.headers.get("X-CSRF-Token", "")
        ):
            raise HTTPException(403, "CSRF token required")
        return identity["username"]

    def admin(username=Depends(actor)):
        if not store.user(username)["admin"]:
            raise HTTPException(403, "Administrator required")
        return username

    @app.middleware("http")
    async def safe(request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin mutation denied"}, status_code=403)
            if (
                request.headers.get("content-type", "").split(";")[0] != "application/json"
                and request.method != "DELETE"
            ):
                return JSONResponse({"detail": "JSON required"}, status_code=415)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 20 * 1024**2:
                    return JSONResponse({"detail": "Import body too large"}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store" if request.url.path.startswith("/v1") else "no-cache",
                "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'",
            }
        )
        return response

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
            secure=os.getenv("RELAYDESK_SECURE_COOKIES") == "1",
            max_age=28800,
            path="/",
        )
        return result

    @app.delete("/v1/auth/session")
    def logout(request: Request, response: Response, username=Depends(actor)):
        store.logout(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE, path="/")
        return {"status": "signed_out"}

    @app.get("/v1/me")
    def me(request: Request, username=Depends(actor)):
        return store.authenticate(request.cookies[COOKIE])

    @app.post("/v1/users")
    def add_user(value: UserCreate, username=Depends(admin)):
        checked(store.add_user, value.username, value.password, value.admin)
        return {"username": value.username}

    @app.get("/v1/accounts")
    def accounts(username=Depends(actor)):
        return store.accounts(username)

    @app.post("/v1/accounts")
    def account(value: Named, username=Depends(actor)):
        return checked(store.create_account, username, value.name)

    @app.post("/v1/accounts/{aid}/cases")
    def new_case(aid: str, value: Named, username=Depends(actor)):
        return checked(store.create_case, username, aid, value.name)

    @app.get("/v1/cases")
    def cases(username=Depends(actor)):
        return store.cases(username)

    @app.get("/v1/cases/{cid}")
    def case(cid: str, username=Depends(actor)):
        scope = checked(store.case, username, cid)
        with store.connect() as db:
            scope["conversations"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM conversations WHERE case_id=? ORDER BY created_at DESC", (cid,)
                )
            ]
            scope["jobs"] = [
                dict(r)
                for r in db.execute(
                    "SELECT id,status,reason,output_id,created_at FROM jobs WHERE case_id=? ORDER BY created_at DESC LIMIT 30",
                    (cid,),
                )
            ]
            scope["members"] = [
                {"username": r[0], "roles": json.loads(r[1])}
                for r in db.execute("SELECT actor,roles FROM members WHERE case_id=?", (cid,))
            ]
        return scope

    @app.put("/v1/cases/{cid}/policy")
    def policy(cid: str, value: Policy, username=Depends(actor)):
        return checked(store.policy, username, cid, value)

    @app.put("/v1/cases/{cid}/members")
    def member(cid: str, value: Membership, username=Depends(actor)):
        checked(store.membership, username, cid, value.username, value.roles)
        return checked(store.case, username, cid)

    @app.post("/v1/cases/{cid}/imports")
    def imported(cid: str, value: ImportBatch, username=Depends(actor)):
        return checked(store.import_messages, username, cid, value)

    @app.post("/v1/cases/{cid}/sources/github")
    def github(cid: str, value: GithubInput, username=Depends(actor)):
        scope = checked(store.case, username, cid, "investigator")
        if value.repository not in scope["policy"].get("github_repositories", []):
            raise HTTPException(403, "Explicit repository read grant required")
        data = checked((sources or GithubSources()).fetch, value.repository, value.issue)
        # Recheck egress/role before persisting a late source response.
        latest = checked(store.case, username, cid, "investigator")
        if value.repository not in latest["policy"].get("github_repositories", []):
            raise HTTPException(403, "Repository grant revoked")
        return checked(store.import_messages, username, cid, data)

    @app.get("/v1/cases/{cid}/memories")
    def memories(
        cid: str, offset: int = 0, limit: int = 100, history: bool = False, username=Depends(actor)
    ):
        if offset < 0 or not 1 <= limit <= 200:
            raise HTTPException(422, "Invalid page bounds")
        rows = checked(store.memories, username, cid, history=history)
        return {
            "items": [
                {k: v for k, v in r.items() if k != "source_body"}
                for r in rows[offset : offset + limit]
            ],
            "total": len(rows),
            "offset": offset,
            "has_more": offset + limit < len(rows),
        }

    @app.get("/v1/sources/{sid}")
    def source(sid: str, username=Depends(actor)):
        return checked(store.source, username, sid)

    @app.post("/v1/memories/{mid}/corrections")
    def correct(mid: str, value: Correction, username=Depends(actor)):
        return checked(
            store.correct,
            username,
            mid,
            value.expected_revision,
            value.text,
            value.kind,
            value.state,
            value.reason,
        )

    @app.post("/v1/memories/{mid}/promotion")
    def promote(mid: str, value: ExpectedRevision, username=Depends(actor)):
        checked(store.promote, username, mid, value.expected_revision)
        return checked(store.memory, username, mid)

    @app.post("/v1/cases/{cid}/erasures")
    def erase(cid: str, value: Erasure, username=Depends(actor)):
        return checked(store.erase, username, cid, value.source_ids, value.confirmation)

    @app.get("/v1/cases/{cid}/changes")
    def changes(cid: str, cursor: int = 0, epoch: str | None = None, username=Depends(actor)):
        return checked(store.changes, username, cid, cursor, epoch)

    @app.get("/v1/cases/{cid}/readiness")
    def readiness(cid: str, username=Depends(actor)):
        scope = checked(store.case, username, cid)
        rows = store.memories(username, cid)
        model = store.setting("encoder", None)
        with store.connect() as db:
            indexed = sum(
                bool(
                    db.execute(
                        "SELECT 1 FROM vectors WHERE memory_id=? AND revision=? AND model=?",
                        (m["id"], m["revision"], model),
                    ).fetchone()
                )
                for m in rows
            )
        return {
            "revision": scope["revision"],
            "model": model,
            "eligible": len(rows),
            "indexed": indexed,
            "pending": len(rows) - indexed,
            "semantic_ready": bool(model) and indexed == len(rows),
        }

    @app.get("/v1/cases/{cid}/summary")
    def summary(cid: str, username=Depends(actor)):
        return compress(checked(store.memories, username, cid))

    @app.post("/v1/cases/{cid}/conversations")
    def conversation(cid: str, username=Depends(actor)):
        return checked(store.conversation, username, cid)

    @app.post("/v1/conversations/{conv}/sessions")
    def session(conv: str, username=Depends(actor)):
        return checked(store.new_session, username, conv)

    @app.get("/v1/conversations/{conv}/messages")
    def turns(conv: str, username=Depends(actor)):
        return checked(store.turns, username, conv)

    @app.post("/v1/conversations/{conv}/messages")
    def message(
        conv: str,
        value: Message,
        key: str = Header(alias="Idempotency-Key"),
        username=Depends(actor),
    ):
        result = checked(store.enqueue, username, conv, value.session_id, value.content, key)
        result.pop("lease", None)
        return result

    @app.post("/v1/cases/{cid}/takeover")
    @app.post("/v1/cases/{cid}/recall")
    def takeover(
        cid: str, value: Recall, key: str = Header(alias="Idempotency-Key"), username=Depends(actor)
    ):
        scope = checked(store.case, username, cid, "investigator")
        if scope["revision"] < value.minimum_revision:
            raise HTTPException(409, "Minimum revision unavailable")
        with store.connect() as db:
            old = db.execute("SELECT * FROM jobs WHERE case_id=? AND key=?", (cid, key)).fetchone()
        if old:
            if (
                old["actor"] != username
                or old["question"] != value.question
                or json.loads(old["options"]) != value.model_dump(exclude={"question"})
            ):
                raise HTTPException(409, "Idempotency key reused with different request")
            result = checked(store.job, username, old["id"])
            result.pop("lease", None)
            return result
        conv = checked(store.conversation, username, cid)
        result = checked(
            store.enqueue,
            username,
            conv["id"],
            conv["session"]["id"],
            value.question,
            key,
            options=value.model_dump(exclude={"question"}),
        )
        result.pop("lease", None)
        return result

    @app.get("/v1/jobs/{jid}")
    def job(jid: str, username=Depends(actor)):
        result = checked(store.job, username, jid)
        result.pop("lease", None)
        return result

    @app.post("/v1/jobs/{jid}/cancel")
    def cancel(jid: str, username=Depends(actor)):
        checked(store.cancel, username, jid)
        return {"status": "requested"}

    @app.post("/v1/jobs/{jid}/continue")
    def continuation(jid: str, key: str = Header(alias="Idempotency-Key"), username=Depends(actor)):
        result = checked(store.continue_job, username, jid, key)
        result.pop("lease", None)
        return result

    @app.get("/v1/handovers/{oid}")
    def output(oid: str, username=Depends(actor)):
        return checked(store.output, username, oid)

    @app.post("/v1/handovers/{oid}/reviews")
    def review(oid: str, value: Review, username=Depends(actor)):
        return checked(store.review, username, oid, value.acknowledge_limits)

    @app.post("/v1/handovers/{oid}/exports")
    def export(oid: str, format: str = "markdown", username=Depends(actor)):
        value = checked(store.export, username, oid)
        if format == "json":
            return JSONResponse(
                value, headers={"Content-Disposition": f"attachment; filename=relaydesk-{oid}.json"}
            )
        if format != "markdown":
            raise HTTPException(422, "Choose markdown or json")
        from relaydesk_api.reports import markdown

        return PlainTextResponse(
            markdown(value),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=relaydesk-{oid}.md"},
        )

    @app.get("/health/live")
    def live():
        return {"product": "relaydesk", "status": "live"}

    @app.get("/health/ready")
    def ready():
        return {
            "product": "relaydesk",
            "storage": True,
            "worker_heartbeat": store.setting("heartbeat"),
            "semantic_model_loaded": bool(store.setting("encoder", None)),
        }

    dist = Path(__file__).resolve().parents[3] / "relaydesk-web" / "dist"

    @app.get("/{path:path}")
    def static(path: str):
        if path.startswith("v1/"):
            raise HTTPException(404, "Endpoint not found")
        target = (dist / path).resolve()
        if not target.is_relative_to(dist.resolve()):
            raise HTTPException(404)
        if target.is_file():
            return FileResponse(target)
        if not (dist / "index.html").exists():
            return PlainTextResponse("Build RelayDesk web client", status_code=503)
        return FileResponse(dist / "index.html")

    return app


def app_from_env():
    return create_app()
