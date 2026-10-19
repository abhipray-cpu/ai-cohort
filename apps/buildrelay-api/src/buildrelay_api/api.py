"""Same-origin workbench and narrow HMAC-authenticated public webhook ingress."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

from contracts.buildrelay import StrictModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from .auth import add_user, login, session
from .github import parse_webhook
from .store import Store


class Credentials(StrictModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1000)


class NewUser(Credentials):
    role: str = Field(pattern="^(owner|operator|viewer)$")
    clients: list[str] = Field(default_factory=list, max_length=100)


class ClientSpec(StrictModel):
    name: str = Field(min_length=1, max_length=150)


class RepoSpec(StrictModel):
    client_id: str = Field(min_length=1, max_length=100)
    name: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)
    github_id: int = Field(gt=0, strict=True)
    secret_ref: str = Field(pattern=r"^BUILDRELAY_[A-Z0-9_]+_SECRET$", max_length=150)
    token_ref: str = Field(pattern=r"^BUILDRELAY_[A-Z0-9_]+_TOKEN$", max_length=150)
    owner: str = Field(min_length=1, max_length=100)
    issues: bool = False


class Reason(StrictModel):
    reason: str = Field(min_length=10, max_length=500)


class ResolveEffect(Reason):
    confirmed_not_created: bool = False


class Acknowledge(Reason):
    owner: str = Field(min_length=1, max_length=100)


class Grants(StrictModel):
    clients: list[str] = Field(max_length=100)


def create_app(data_dir, *, username, password, secure=False):
    if not username or len(password) < 12 or password == "replace-me":
        raise ValueError("explicit username and password of at least 12 characters required")
    store = Store(data_dir)
    with store.connect() as db:
        empty = not db.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if empty:
        add_user(store, username, password, "owner")
    app = FastAPI(title="BuildRelay", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    failures = {}

    @app.middleware("http")
    async def boundaries(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    return JSONResponse({"detail": "request too large"}, status_code=413)
            request._body = bytes(body)
        if request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if (
                request.method not in {"GET", "HEAD"}
                and origin
                and origin != str(request.base_url).rstrip("/")
            ):
                return JSONResponse({"detail": "origin denied"}, status_code=403)
            if request.url.path != "/api/session":
                actor = session(store, request.cookies.get("buildrelay_session", ""))
                if not actor:
                    return JSONResponse({"detail": "authentication required"}, status_code=401)
                request.state.actor = actor
                if request.method not in {"GET", "HEAD"} and not secrets.compare_digest(
                    request.headers.get("X-CSRF-Token", "").encode(), actor["csrf"].encode()
                ):
                    return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
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
        return JSONResponse({"detail": "not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def conflict(request, exc):
        return JSONResponse({"detail": "operation conflicts with current state"}, status_code=409)

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity(request, exc):
        return JSONResponse({"detail": "duplicate or invalid reference"}, status_code=409)

    def actor(request, roles=None):
        a = request.state.actor
        if roles and a["role"] not in roles:
            raise HTTPException(403, "capability denied")
        return a

    def allowed(a, repo):
        return a["role"] == "owner" or repo["client_id"] in a["clients"]

    def scoped_repo(request, ident):
        repo = store.repo(ident)
        if not allowed(actor(request), repo):
            raise HTTPException(404, "not found")
        return repo

    def scoped_event(request, ident):
        with store.connect() as db:
            row = db.execute("SELECT * FROM events WHERE id=?", (ident,)).fetchone()
        if not row:
            raise HTTPException(404, "not found")
        scoped_repo(request, row["repo_id"])
        return dict(row)

    @app.get("/health/ready")
    def health():
        beats = {b["name"]: b for b in store.rows("heartbeat")}
        healthy = "workflow" in beats and time.time() - beats["workflow"]["updated"] < 600
        if os.environ.get("BUILDRELAY_NATS_URL"):
            healthy &= (
                "queue" in beats
                and time.time() - beats["queue"]["updated"] < 30
                and beats["queue"]["detail"] == "connected"
            )
        return JSONResponse(
            {"status": "ready" if healthy else "degraded", "ai_acceptance": "unverified"},
            status_code=200 if healthy else 503,
        )

    @app.post("/hooks/github/{repo_id}", status_code=202)
    async def hook(repo_id: str, request: Request):
        try:
            repo = store.repo(repo_id)
        except KeyError:
            raise HTTPException(404, "unknown webhook") from None
        key = os.environ.get(repo["secret_ref"], "")
        if len(key) < 12:
            raise HTTPException(503, "webhook secret not configured")
        raw = await request.body()
        expected = "sha256=" + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(
            expected.encode(), request.headers.get("X-Hub-Signature-256", "").encode()
        ):
            raise HTTPException(401, "signature denied")
        delivery = request.headers.get("X-GitHub-Delivery", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", delivery):
            raise HTTPException(400, "delivery ID required")
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise TypeError("object required")
            event = parse_webhook(request.headers.get("X-GitHub-Event", ""), body)
            if event is None:
                return {"accepted": False, "reason": "event not subscribed"}
            ident = store.accept(repo_id, event, "webhook", delivery)
        except (ValueError, TypeError):
            raise HTTPException(422, "invalid event or repository binding") from None
        return {"accepted": True, "event_id": ident}

    @app.post("/api/session")
    def signin(request: Request, body: Credentials):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Bounded in-process throttle; gateway must provide distributed/rate controls in production.
        if len(failures) > 2000:
            failures.clear()
        failures[ip] = [t for t in failures.get(ip, []) if t > now - 60]
        if len(failures[ip]) >= 10:
            raise HTTPException(429, "login rate limited")
        result = login(store, body.username, body.password)
        if not result:
            failures[ip].append(now)
            raise HTTPException(401, "invalid credentials")
        token, csrf = result
        response = JSONResponse({"csrf": csrf, "name": body.username})
        response.set_cookie(
            "buildrelay_session",
            token,
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=28800,
        )
        return response

    @app.get("/api/session")
    def who(request: Request):
        a = session(store, request.cookies.get("buildrelay_session", ""))
        if not a:
            raise HTTPException(401, "authentication required")
        return a

    @app.delete("/api/session")
    def logout(request: Request):
        token = request.cookies.get("buildrelay_session", "")
        a = session(store, token)
        if not a or not hmac.compare_digest(
            a["csrf"].encode(), request.headers.get("X-CSRF-Token", "").encode()
        ):
            raise HTTPException(403, "CSRF check failed")
        with store.write() as db:
            db.execute(
                "DELETE FROM sessions WHERE token=?", (hashlib.sha256(token.encode()).hexdigest(),)
            )
        r = JSONResponse({"logged_out": True})
        r.delete_cookie("buildrelay_session")
        return r

    @app.get("/api/overview")
    def overview(request: Request):
        a = actor(request)
        repos = [r for r in store.repos() if allowed(a, r)]
        ids = {r["id"] for r in repos}
        clients = [
            c for c in store.rows("clients") if a["role"] == "owner" or c["id"] in a["clients"]
        ]
        return {
            "clients": clients,
            "repos": repos,
            "events": [
                {k: v for k, v in e.items() if k not in {"checkpoint", "lease_token"}}
                for e in store.events()
                if e["repo_id"] in ids
            ],
            "incidents": [
                dict(i, triage=json.loads(i["triage"]) if i["triage"] else None)
                for i in store.incidents()
                if i["repo_id"] in ids
            ],
            "audit": [
                r
                for r in store.audit()
                if r["repo_id"] in ids or (a["role"] == "owner" and r["repo_id"] is None)
            ],
            "heartbeat": store.rows("heartbeat") if a["role"] == "owner" else [],
            "queue_enabled": bool(os.environ.get("BUILDRELAY_NATS_URL")),
            "ai_acceptance": "unverified",
        }

    @app.get("/api/events/{ident}")
    def detail(ident: str, request: Request):
        e = scoped_event(request, ident)
        e.pop("lease_token", None)
        e["checkpoint"] = json.loads(e["checkpoint"])
        e["payload"] = json.loads(e["payload"])
        from contracts.buildrelay import RunEvent

        incident_id = store.incident_id(e["repo_id"], RunEvent.model_validate(e["payload"]))
        e["incident_id"] = incident_id
        e["effect"] = store.effect(incident_id)
        return e

    @app.post("/api/incidents/{ident}/acknowledge")
    def acknowledge(ident: str, request: Request, body: Acknowledge):
        a = actor(request, {"owner", "operator"})
        incident = store.incident(ident)
        if not incident:
            raise HTTPException(404, "not found")
        scoped_repo(request, incident["repo_id"])
        with store.write() as db:
            db.execute(
                "UPDATE incidents SET owner=?,updated=? WHERE id=?",
                (body.owner, time.time(), ident),
            )
            store.record(
                db,
                "incident_acknowledged",
                repo_id=incident["repo_id"],
                actor=a["name"],
                detail={"incident_id": ident, "owner": body.owner, "reason": body.reason},
            )
        return {"acknowledged": True, "external_issue_owner_note": "updated on next run event"}

    @app.get("/api/incidents/{ident}/export")
    def export(ident: str, request: Request):
        incident = store.incident(ident)
        if not incident:
            raise HTTPException(404, "not found")
        scoped_repo(request, incident["repo_id"])
        incident["triage"] = json.loads(incident["triage"]) if incident["triage"] else None
        return JSONResponse(
            {
                "incident": incident,
                "client_update_approved": False,
                "limitations": "Self-assessed confidence; observed recovery is not a verified fix. Evidence line numbers refer to captured log excerpts.",
            },
            headers={"Content-Disposition": f'attachment; filename="buildrelay-{ident[:12]}.json"'},
        )

    @app.post("/api/clients", status_code=201)
    def clients(request: Request, body: ClientSpec):
        a = actor(request, {"owner"})
        ident = uuid.uuid4().hex
        store.create_client(ident, body.name, actor=a["name"])
        return {"id": ident}

    @app.post("/api/repos", status_code=201)
    def repos(request: Request, body: RepoSpec):
        a = actor(request, {"owner"})
        ident = uuid.uuid4().hex
        store.create_repo(
            ident,
            body.client_id,
            body.name,
            body.github_id,
            body.secret_ref,
            body.token_ref,
            body.owner,
            body.issues,
            actor=a["name"],
        )
        return {"id": ident, "webhook_path": f"/hooks/github/{ident}"}

    @app.post("/api/users", status_code=201)
    def users(request: Request, body: NewUser):
        a = actor(request, {"owner"})
        add_user(store, body.username, body.password, body.role, body.clients)
        with store.write() as db:
            store.record(
                db,
                "user_created",
                actor=a["name"],
                detail={"name": body.username, "role": body.role, "clients": body.clients},
            )
        return {"created": True}

    @app.get("/api/users")
    def list_users(request: Request):
        actor(request, {"owner"})
        with store.connect() as db:
            return [
                {
                    "name": u["name"],
                    "role": u["role"],
                    "clients": [
                        g[0]
                        for g in db.execute(
                            "SELECT client_id FROM grants WHERE name=?", (u["name"],)
                        )
                    ],
                }
                for u in db.execute("SELECT name,role FROM users ORDER BY name")
            ]

    @app.put("/api/users/{name}/grants")
    def update_grants(name: str, request: Request, body: Grants):
        a = actor(request, {"owner"})
        with store.write() as db:
            if not db.execute("SELECT 1 FROM users WHERE name=?", (name,)).fetchone():
                raise HTTPException(404, "not found")
            for client in body.clients:
                if not db.execute("SELECT 1 FROM clients WHERE id=?", (client,)).fetchone():
                    raise HTTPException(409, "unknown client")
            db.execute("DELETE FROM grants WHERE name=?", (name,))
            db.executemany("INSERT INTO grants VALUES(?,?)", [(name, c) for c in set(body.clients)])
            store.record(
                db,
                "client_grants_changed",
                actor=a["name"],
                detail={"name": name, "clients": body.clients},
            )
        return {"updated": True}

    @app.delete("/api/users/{name}")
    def revoke_user(name: str, request: Request):
        a = actor(request, {"owner"})
        with store.write() as db:
            row = db.execute("SELECT role FROM users WHERE name=?", (name,)).fetchone()
            if not row:
                raise HTTPException(404, "not found")
            if (
                row[0] == "owner"
                and db.execute("SELECT count(*) FROM users WHERE role='owner'").fetchone()[0] <= 1
            ):
                raise HTTPException(409, "cannot remove last owner")
            db.execute("DELETE FROM sessions WHERE name=?", (name,))
            db.execute("DELETE FROM grants WHERE name=?", (name,))
            db.execute("DELETE FROM users WHERE name=?", (name,))
            store.record(db, "user_revoked", actor=a["name"], detail={"name": name})
        return {"revoked": True}

    @app.post("/api/events/{ident}/replay")
    def replay(ident: str, request: Request, body: Reason):
        a = actor(request, {"owner", "operator"})
        scoped_event(request, ident)
        store.replay(ident, a["name"], reason=body.reason)
        return {"queued": True}

    @app.post("/api/repos/{ident}/reconcile")
    def reconcile(ident: str, request: Request, body: Reason):
        a = actor(request, {"owner", "operator"})
        scoped_repo(request, ident)
        with store.write() as db:
            db.execute("DELETE FROM cursors WHERE repo_id=?", (ident,))
            store.record(db, "reconciliation_requested", repo_id=ident, actor=a["name"])
        return {"scheduled": True}

    @app.post("/api/effects/{ident}/confirm-not-created")
    def resolve_effect(ident: str, request: Request, body: ResolveEffect):
        a = actor(request, {"owner"})
        incident = store.incident(ident)
        if not incident:
            raise HTTPException(404, "not found")
        scoped_repo(request, incident["repo_id"])
        if not body.confirmed_not_created:
            raise HTTPException(409, "explicit external verification required")
        with store.write() as db:
            row = db.execute("SELECT * FROM effects WHERE incident_id=?", (ident,)).fetchone()
            if not row or row["state"] not in {"sending", "uncertain"} or row["external_id"]:
                raise HTTPException(409, "effect is not unresolved")
            if db.execute("SELECT 1 FROM events WHERE state='processing'").fetchone():
                raise HTTPException(409, "wait for active worker to finish")
            db.execute("DELETE FROM effects WHERE incident_id=?", (ident,))
            store.record(
                db,
                "effect_rearmed_after_human_verification",
                repo_id=incident["repo_id"],
                actor=a["name"],
                detail={"incident_id": ident, "reason": body.reason},
            )
        return {"rearmed": True, "next": "replay dead letter"}

    web = Path(__file__).resolve().parents[3] / "buildrelay-web" / "dist"
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="workbench")
    return app


def app_from_env():
    return create_app(
        os.environ.get("BUILDRELAY_DATA_DIR", "var/buildrelay"),
        username=os.environ.get("BUILDRELAY_USERNAME", ""),
        password=os.environ.get("BUILDRELAY_PASSWORD", ""),
        secure=os.environ.get("BUILDRELAY_SECURE_COOKIES", "false").lower() == "true",
    )
