"""Same-origin authenticated CatalogBridge API and static workbench."""

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

from contracts.catalogbridge import BatchSpec, Calibration, Review
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .auth import add_user, login, session
from .ingest import parse_feed
from .local_router import configured_router
from .store import Store


def settings():
    root = Path(os.environ.get("CATALOGBRIDGE_DATA_DIR", "var/catalogbridge"))
    return {
        "data_dir": root,
        "journal_dir": os.environ.get("CATALOGBRIDGE_USAGE_JOURNAL_DIR"),
        "username": os.environ.get("CATALOGBRIDGE_USERNAME", ""),
        "password": os.environ.get("CATALOGBRIDGE_PASSWORD", ""),
        "secure": os.environ.get("CATALOGBRIDGE_SECURE_COOKIES", "false").lower() == "true",
    }


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1000)


class RuntimeAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=12, max_length=2000)


class Increase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tokens: int = Field(gt=0, le=100000000, strict=True)


class NewUser(Credentials):
    role: str


def create_app(data_dir, *, username, password, journal_dir=None, secure=False):
    store = Store(data_dir, journal_dir)
    with store.connect() as db:
        exists = db.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if not exists:
        add_user(store, username, password, "default", "owner")
    app = FastAPI(title="CatalogBridge", docs_url=None, redoc_url=None)
    app.state.store = store
    failures = {}

    @app.middleware("http")
    async def boundaries(request, call_next):
        if request.url.path.startswith("/api/") and request.url.path != "/api/session":
            actor = session(store, request.cookies.get("catalogbridge_session", ""))
            if not actor:
                return JSONResponse({"detail": "authentication required"}, status_code=401)
            request.state.actor = actor
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", ""), actor["csrf"]
            ):
                return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and origin != str(request.base_url).rstrip("/")
        ):
            return JSONResponse({"detail": "origin denied"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)[:300]}, status_code=409)

    def actor(request, roles=None):
        a = request.state.actor
        if roles and a["role"] not in roles:
            raise HTTPException(403, "capability denied")
        return a

    @app.get("/health/ready")
    def health():
        return {"status": "ready", "ai_acceptance": "unverified", "hard_token_limit": False}

    @app.post("/api/session")
    def signin(request: Request, credentials: Credentials):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        failures[ip] = [v for v in failures.get(ip, []) if v > now - 60]
        if len(failures[ip]) >= 10:
            raise HTTPException(429, "login rate limited")
        result = login(store, credentials.username, credentials.password)
        if not result:
            failures[ip].append(now)
            raise HTTPException(401, "invalid credentials")
        token, csrf = result
        a = session(store, token)
        response = JSONResponse({"csrf": csrf, "name": a["name"], "role": a["role"]})
        response.set_cookie(
            "catalogbridge_session",
            token,
            httponly=True,
            samesite="strict",
            secure=secure,
            max_age=28800,
        )
        return response

    @app.get("/api/session")
    def who(request: Request):
        a = session(store, request.cookies.get("catalogbridge_session", ""))
        if not a:
            raise HTTPException(401, "authentication required")
        return a

    @app.delete("/api/session")
    def logout(request: Request):
        a = session(store, request.cookies.get("catalogbridge_session", ""))
        if not a or not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), a["csrf"]):
            raise HTTPException(403, "CSRF check failed")
        with store.write() as db:
            db.execute(
                "DELETE FROM sessions WHERE token=?",
                (hashlib.sha256(request.cookies["catalogbridge_session"].encode()).hexdigest(),),
            )
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("catalogbridge_session")
        return response

    @app.post("/api/users")
    def users(request: Request, body: NewUser):
        a = actor(request, {"owner"})
        add_user(store, body.username, body.password, a["workspace"], body.role)
        return {"created": True}

    @app.get("/api/routing-profile")
    def routing_profile(request: Request):
        actor(request)
        try:
            local = configured_router()
        except (ValueError, OSError, RecursionError):
            return {"available": False, "automatic_acceptance": False}
        return {
            "available": True,
            "sha256": local.fingerprint,
            "evidence_scope": local.profile.evidence_scope,
            "automatic_acceptance": False,
            "bands": {
                name: band.model_dump() for name, band in local.profile.qualification.items()
            },
        }

    @app.get("/api/feeds")
    def feeds(request: Request):
        a = actor(request)
        with store.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,kind,hash FROM feeds WHERE workspace=?", (a["workspace"],)
                )
            ]

    @app.post("/api/feeds")
    async def upload(request: Request, kind: str = Query(...), format: str = "csv"):
        a = actor(request, {"owner", "operator"})
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(413, "feed too large")
        try:
            rows = parse_feed(bytes(data), format)
            return store.import_feed(a["workspace"], kind, rows)
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, str(exc)[:300]) from exc

    @app.get("/api/feeds/{feed_id}")
    def source(request: Request, feed_id: str, offset: int = Query(0, ge=0)):
        a = actor(request)
        feed = store.feed(a["workspace"], feed_id)
        return {**feed, "records": [r.model_dump() for r in feed["records"][offset : offset + 50]]}

    @app.post("/api/batches")
    def create(request: Request, body: BatchSpec):
        a = actor(request, {"owner"})
        if body.calibration_id and not body.calibration_id.startswith(a["workspace"] + ":"):
            raise HTTPException(403, "calibration scope denied")
        key = request.headers.get("Idempotency-Key")
        if key and len(key) > 200:
            raise HTTPException(422, "idempotency key too long")
        return store.create_batch(a["workspace"], body, key)

    @app.get("/api/feeds/{feed_id}/record")
    def record(request: Request, feed_id: str, id: str):
        a = actor(request)
        found = next(
            (r for r in store.feed(a["workspace"], feed_id)["records"] if r.id == id), None
        )
        if not found:
            raise KeyError("record not found")
        return found.model_dump()

    @app.get("/api/batches")
    def batches(request: Request):
        return store.batches(actor(request)["workspace"])

    @app.get("/api/batches/{batch_id}")
    def batch(request: Request, batch_id: str):
        return store.batch(actor(request)["workspace"], batch_id)

    @app.post("/api/batches/{batch_id}/start")
    @app.post("/api/batches/{batch_id}/continue")
    def start(request: Request, batch_id: str):
        a = actor(request, {"owner", "operator"})
        store.start(a["workspace"], batch_id)
        return {"queued": True}

    @app.post("/api/batches/{batch_id}/cancel")
    def cancel(request: Request, batch_id: str):
        a = actor(request, {"owner", "operator"})
        store.cancel(a["workspace"], batch_id)
        return {"cancelled": True}

    @app.get("/api/batches/{batch_id}/tasks")
    def tasks(
        request: Request,
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        return store.tasks(actor(request)["workspace"], batch_id, offset, limit)

    @app.post("/api/tasks/{task_id}/review")
    def review(request: Request, task_id: str, body: Review):
        a = actor(request, {"owner", "reviewer"})
        store.review(a["workspace"], task_id, a["name"], body)
        return {"saved": True}

    @app.get("/api/batches/{batch_id}/analytics")
    def analytics(request: Request, batch_id: str):
        return store.analytics(actor(request)["workspace"], batch_id)

    @app.get("/api/runtime")
    def runtime_status(request: Request):
        return store.runtime_status(actor(request)["workspace"])

    @app.post("/api/runtime/acknowledge")
    def acknowledge_runtime(request: Request, body: RuntimeAcknowledgement):
        a = actor(request, {"owner"})
        store.acknowledge_runtime(a["workspace"], a["name"], body.reason)
        return {**store.runtime_status(a["workspace"]), "health_verified": False}

    @app.get("/api/batches/{batch_id}/audit")
    def audit(request: Request, batch_id: str):
        return store.audit(actor(request)["workspace"], batch_id)

    @app.post("/api/batches/{batch_id}/exports")
    def export(request: Request, batch_id: str):
        a = actor(request, {"owner", "reviewer"})
        csv, manifest = store.export(a["workspace"], batch_id)
        return {"csv": csv, "manifest": manifest}

    @app.post("/api/batches/{batch_id}/budget-increases")
    def increase(request: Request, batch_id: str, body: Increase):
        a = actor(request, {"owner"})
        store.batch(a["workspace"], batch_id)
        with store.write() as db:
            original = db.execute("SELECT spec FROM batches WHERE id=?", (batch_id,)).fetchone()[0]
            spec = BatchSpec.model_validate_json(original)
            spec = BatchSpec.model_validate(
                spec.model_dump() | {"token_budget": spec.token_budget + body.tokens}
            )
            db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), batch_id))
            store.event(
                db,
                batch_id,
                "budget_increase",
                {
                    "actor": a["name"],
                    "additional": body.tokens,
                    "previous": json.loads(original)["token_budget"],
                },
            )
        return {"token_budget": spec.token_budget}

    @app.post("/api/calibrations")
    def calibrate(request: Request, body: Calibration):
        a = actor(request, {"owner"})
        if body.evidence_status != "operator_attested":
            raise HTTPException(
                409, "Owner upload cannot establish independent empirical qualification"
            )
        # Operator-provided evidence is not independently verified by accepting this file.
        with store.write() as db:
            db.execute(
                "INSERT INTO calibrations VALUES(?,?)",
                (a["workspace"] + ":" + body.id, body.model_dump_json()),
            )
        return {
            "id": a["workspace"] + ":" + body.id,
            "evidence_status": "operator_attested_not_independently_verified",
        }

    dist = Path(__file__).resolve().parents[3] / "catalogbridge-web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


def app_from_env():
    return create_app(
        **{k: v for k, v in settings().items() if k != "secure"}, secure=settings()["secure"]
    )
