"""Authenticated tenant API, bounded machine intake and same-origin release desk."""

import hmac
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated, Literal

import psycopg
from contracts.releasefence import Contract, Digest, Event, Identifier, Policy, Release, Timestamp
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, StrictBool, StrictInt

from .core import digest
from .errors import Conflict, Forbidden
from .telemetry import normalize_otlp, protobuf_payload


class Login(Contract):
    username: Annotated[str, Field(min_length=1, max_length=100)]
    password: Annotated[str, Field(min_length=1, max_length=512)]


class Name(Contract):
    name: Annotated[str, Field(min_length=1, max_length=150)]


class Member(Contract):
    username: Annotated[str, Field(min_length=1, max_length=100)]
    role: Literal["owner", "operator", "approver", "observer"]


class Environment(Contract):
    application: Identifier
    environment: Identifier
    stable: Digest


class Enrollment(Contract):
    application: Identifier
    environment: Identifier
    public_key: Annotated[str, Field(min_length=40, max_length=60)]
    mode: Literal["observe", "controlled"]


class Rollout(Contract):
    application: Identifier
    environment: Identifier
    stable: Digest
    candidate: Digest
    policy: Policy
    enrollments: Annotated[list[Identifier], Field(min_length=1, max_length=100)]
    expires: Timestamp


class Approval(Contract):
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    actions: Annotated[
        list[Literal["canary", "promote", "rollback"]], Field(min_length=1, max_length=3)
    ]
    expires: Timestamp
    auto_rollback: StrictBool = False


class Control(Contract):
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    action: Literal["canary", "promote", "rollback"]


class Recovery(Contract):
    expires: Timestamp


class Revision(Contract):
    expected_revision: Annotated[StrictInt, Field(ge=0)]


class Destination(Contract):
    url: Annotated[str, Field(min_length=1, max_length=2000)]
    secret: Annotated[str, Field(min_length=24, max_length=512)]


class Events(Contract):
    events: Annotated[list[Event], Field(max_length=100)]


class BackendConfig(Contract):
    kind: Literal["langsmith", "phoenix", "mlflow"]
    export_url: Annotated[str, Field(min_length=1, max_length=2000)]
    read_url: Annotated[str, Field(min_length=1, max_length=2000)]
    secret: Annotated[str, Field(min_length=1, max_length=512)]
    project: Annotated[str, Field(min_length=1, max_length=128)]


class Registration(Contract):
    application: Identifier
    environment: Identifier
    expires: Timestamp


class Resolution(Contract):
    note: Annotated[str, Field(min_length=12, max_length=500)]


class ConnectionState(Contract):
    enabled: StrictBool


def create_app(store, *, origin, administrator, web_root=None, lab_loopback=False):
    app = FastAPI(
        title="ReleaseFence", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None
    )
    rate = defaultdict(deque)

    @app.middleware("http")
    async def boundary(request, call_next):
        if request.headers.get("content-encoding", "identity") != "identity":
            return JSONResponse({"detail": "compressed requests unsupported"}, 415)
        try:
            if int(request.headers.get("content-length", "0")) > 1048576:
                return JSONResponse({"detail": "request too large"}, 413)
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > 1048576:
                    return JSONResponse({"detail": "request too large"}, 413)
            request._body = bytes(content)
            if content and "json" in request.headers.get("content-type", ""):

                def unique(pairs):
                    obj = {}
                    for key, value in pairs:
                        if key in obj:
                            raise ValueError("duplicate field")
                        obj[key] = value
                    return obj

                data = json.loads(
                    content,
                    object_pairs_hook=unique,
                    parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite")),
                )

                def depth(value, n=0):
                    if isinstance(value, (dict, list)) and n > 10:
                        raise ValueError("nesting exceeds bound")
                    if isinstance(value, dict):
                        for v in value.values():
                            depth(v, n + 1)
                    elif isinstance(value, list):
                        for v in value:
                            depth(v, n + 1)

                depth(data)
        except (ValueError, RecursionError):
            return JSONResponse({"detail": "invalid bounded JSON"}, 422)
        key = (
            request.client.host if request.client else "unknown",
            digest(request.headers.get("authorization", "").encode())
            if request.headers.get("authorization")
            else "browser",
        )
        now = time.monotonic()
        if len(rate) > 10000 and key not in rate:
            return JSONResponse({"detail": "rate capacity"}, 429)
        q = rate[key]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= (1000 if key[1] != "browser" else 300):
            return JSONResponse({"detail": "rate limited"}, 429)
        q.append(now)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'",
            }
        )
        return response

    @app.exception_handler(Forbidden)
    async def forbidden(request, exc):
        return JSONResponse({"detail": "object unavailable or action forbidden"}, 403)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": "state, authority or revision conflict"}, 409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": "invalid input or evidence"}, 422)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse(
            {
                "detail": "request contract validation failed",
                "fields": [{"loc": e["loc"], "type": e["type"]} for e in exc.errors()],
            },
            422,
        )

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        return JSONResponse({"detail": "database unavailable or state conflict"}, 503)

    def session(request: Request):
        try:
            auth = store.session(request.cookies.get("releasefence_session", ""))
        except Forbidden:
            raise HTTPException(401, "session required") from None
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            request.headers.get("origin") != origin
            or not hmac.compare_digest(request.headers.get("x-csrf-token", ""), auth["csrf"])
        ):
            raise Forbidden("CSRF context")
        return auth

    def machine(request: Request):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or len(auth) > 256:
            raise HTTPException(401, "machine credential required")
        return store.machine(auth[7:])

    def scope(id, auth):
        if id != auth["enrollment"]:
            raise Forbidden("connector scope")

    def idem(key):
        if not key or not 1 <= len(key) <= 128:
            raise ValueError("idempotency key required")
        return key

    @app.get("/health/live")
    def live():
        return {"live": True}

    @app.get("/health/ready")
    def ready():
        try:
            with store.db() as db:
                worker = db.execute(
                    "SELECT heartbeat FROM worker_status WHERE id='engine'"
                ).fetchone()
            good = bool(worker and store.now() - worker["heartbeat"] < 30)
            return JSONResponse(
                {
                    "ready": good,
                    "database": True,
                    "worker_seen": good,
                    "trace_qualification": "see_organization_backend_proofs",
                },
                200 if good else 503,
            )
        except psycopg.Error:
            return JSONResponse({"ready": False, "database": False}, 503)

    login_failures = defaultdict(deque)

    @app.post("/api/session")
    def login(body: Login, request: Request):
        if request.headers.get("origin") not in {None, origin}:
            raise Forbidden("origin")
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = login_failures[key]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= 5:
            raise HTTPException(429, "login throttled")
        try:
            token, csrf = store.login(body.username, body.password)
        except Forbidden:
            q.append(now)
            raise
        q.clear()
        response = JSONResponse({"actor": body.username, "csrf": csrf})
        response.set_cookie(
            "releasefence_session",
            token,
            httponly=True,
            samesite="strict",
            secure=origin.startswith("https://"),
            max_age=28800,
        )
        return response

    @app.get("/api/session")
    def current(auth=Depends(session)):
        return {"actor": auth["actor"], "csrf": auth["csrf"]}

    @app.post("/api/session/logout")
    def logout(request: Request, auth=Depends(session)):
        store.logout(request.cookies.get("releasefence_session", ""))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("releasefence_session")
        return response

    @app.post("/api/users")
    def user(body: Login, auth=Depends(session)):
        if auth["actor"] != administrator:
            raise Forbidden("platform operator required")
        store.create_user(body.username, body.password)
        return {"created": True}

    @app.get("/api/orgs")
    def orgs(auth=Depends(session)):
        return store.organizations(auth["actor"])

    @app.post("/api/orgs")
    def create_org(body: Name, auth=Depends(session)):
        return {"id": store.create_org(auth["actor"], body.name)}

    @app.post("/api/orgs/{tenant}/members")
    def member(tenant: str, body: Member, auth=Depends(session)):
        store.member(auth["actor"], tenant, body.username, body.role)
        return {"updated": True}

    @app.post("/api/orgs/{tenant}/release")
    def release(tenant: str, body: Release, auth=Depends(session)):
        return {"id": store.release(auth["actor"], tenant, body)}

    @app.post("/api/orgs/{tenant}/environment")
    def environment(tenant: str, body: Environment, auth=Depends(session)):
        return {"id": store.environment(auth["actor"], tenant, **body.model_dump())}

    @app.post("/api/orgs/{tenant}/enrollment")
    def enroll(tenant: str, body: Enrollment, auth=Depends(session)):
        return store.enroll(
            auth["actor"], tenant, body.application, body.environment, body.public_key, body.mode
        )

    @app.post("/api/orgs/{tenant}/enrollment/{id}/revoke")
    def revoke(tenant: str, id: str, auth=Depends(session)):
        store.revoke(auth["actor"], tenant, id)
        return {"revoked": True}

    @app.post("/api/orgs/{tenant}/destination")
    def destination(
        tenant: str,
        body: Destination,
        key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        auth=Depends(session),
    ):
        return {
            "id": store.destination(
                auth["actor"], tenant, body.url, body.secret, idem(key), lab_loopback=lab_loopback
            )
        }

    @app.post("/api/orgs/{tenant}/backend")
    def backend(
        tenant: str,
        body: BackendConfig,
        key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        auth=Depends(session),
    ):
        return {
            "id": store.backend(
                auth["actor"], tenant, **body.model_dump(), key=idem(key), lab_loopback=lab_loopback
            )
        }

    @app.post("/api/orgs/{tenant}/rollout")
    def rollout(
        tenant: str,
        body: Rollout,
        key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        auth=Depends(session),
    ):
        return {
            "id": store.create_rollout(
                auth["actor"],
                tenant,
                **body.model_dump(exclude={"policy"}),
                policy=body.policy,
                key=idem(key),
            )
        }

    @app.post("/api/orgs/{tenant}/rollout/{id}/approve")
    def approve(
        tenant: str,
        id: str,
        body: Approval,
        key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        auth=Depends(session),
    ):
        return {
            "id": store.approve(
                auth["actor"],
                tenant,
                id,
                body.expected_revision,
                body.actions,
                body.expires,
                idem(key),
                auto_rollback=body.auto_rollback,
            )
        }

    @app.post("/api/orgs/{tenant}/rollout/{id}/control")
    def control(
        tenant: str,
        id: str,
        body: Control,
        key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        auth=Depends(session),
    ):
        return {
            "commands": store.control(
                auth["actor"], tenant, id, body.action, body.expected_revision, idem(key)
            )
        }

    @app.post("/api/orgs/{tenant}/rollout/{id}/analyze")
    def analyze(tenant: str, id: str, auth=Depends(session)):
        return store.analyze_rollout(auth["actor"], tenant, id)

    @app.post("/api/orgs/{tenant}/rollout/{id}/recover")
    def recover(tenant: str, id: str, body: Recovery, auth=Depends(session)):
        store.recover(auth["actor"], tenant, id, body.expires)
        return {"new_independent_rollback_approval_required": True}

    @app.post("/api/orgs/{tenant}/rollout/{id}/cancel")
    def cancel(tenant: str, id: str, body: Revision, auth=Depends(session)):
        store.cancel(auth["actor"], tenant, id, body.expected_revision)
        return {"cancelled": True}

    @app.get("/api/orgs/{tenant}/rollout/{id}/evidence")
    def evidence(tenant: str, id: str, auth=Depends(session)):
        return store.evidence(auth["actor"], tenant, id)

    @app.post("/api/orgs/{tenant}/approval/{id}/revoke")
    def revoke_approval(tenant: str, id: str, auth=Depends(session)):
        store.revoke_approval(auth["actor"], tenant, id)
        return {"revoked": True}

    @app.get("/api/orgs/{tenant}/views/metrics")
    def metric_view(tenant: str, application: str, environment: str, auth=Depends(session)):
        return {
            k: {n: v for n, v in values.items() if n != "observations"}
            for k, values in store.metric_view(
                auth["actor"], tenant, application, environment
            ).items()
        }

    @app.post("/api/orgs/{tenant}/incident/{id}/acknowledge")
    def ack(tenant: str, id: str, auth=Depends(session)):
        store.acknowledge(auth["actor"], tenant, id)
        return {"acknowledged": True}

    @app.post("/api/orgs/{tenant}/incident/{id}/resolve")
    def resolve(tenant: str, id: str, body: Resolution, auth=Depends(session)):
        store.resolve(auth["actor"], tenant, id, body.note)
        return {"resolved": True}

    @app.post("/api/orgs/{tenant}/notification/{id}/replay")
    def replay(tenant: str, id: str, auth=Depends(session)):
        store.notification_replay(auth["actor"], tenant, id)
        return {"queued": True}

    @app.post("/api/orgs/{tenant}/trace_export/{id}/replay")
    def trace_replay(tenant: str, id: str, auth=Depends(session)):
        store.replay_trace(auth["actor"], tenant, id)
        return {"queued": True}

    @app.post("/api/orgs/{tenant}/connection/{kind}/{id}/state")
    def connection_state(
        tenant: str, kind: str, id: str, body: ConnectionState, auth=Depends(session)
    ):
        store.set_connection(auth["actor"], tenant, kind, id, body.enabled)
        return {"enabled": body.enabled}

    @app.post("/ingest/v1/events")
    def events(body: Events, auth=Depends(machine)):
        return {"accepted": store.ingest(auth, body.events)}

    @app.post("/api/orgs/{tenant}/registration")
    def registration(tenant: str, body: Registration, auth=Depends(session)):
        return store.registration_token(auth["actor"], tenant, **body.model_dump())

    @app.post("/registry/v1/releases")
    def ci_release(body: Release, request: Request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            raise Forbidden("credential required")
        return {"id": store.ci_release(header[7:], body)}

    @app.post("/api/orgs/{tenant}/registration/{id}/revoke")
    def revoke_registration(tenant: str, id: str, auth=Depends(session)):
        store.revoke_registration(auth["actor"], tenant, id)
        return {"revoked": True}

    @app.post("/ingest/v1/traces")
    async def traces(request: Request, auth=Depends(machine)):
        from google.protobuf.message import DecodeError

        try:
            payload = (
                protobuf_payload(await request.body())
                if request.headers.get("content-type", "").startswith("application/x-protobuf")
                else json.loads(await request.body())
            )
            values = normalize_otlp(payload)
        except (DecodeError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError("invalid OTLP") from exc
        return {"accepted": store.ingest_spans(auth, values)}

    @app.post("/connector/v1/{id}/heartbeat")
    def heartbeat(id: str, body: dict, auth=Depends(machine)):
        scope(id, auth)
        store.heartbeat(auth, body)
        return {"accepted": True}

    @app.post("/connector/v1/{id}/poll")
    def poll(id: str, auth=Depends(machine)):
        scope(id, auth)
        return {"commands": store.poll(auth), "window": store.counter_window(auth)}

    @app.post("/connector/v1/{id}/commands/{command}/authorize")
    def authorize(id: str, command: str, auth=Depends(machine)):
        scope(id, auth)
        return {"authorized": store.authorize_command(auth, command)}

    @app.post("/connector/v1/{id}/attest")
    def attest(id: str, body: dict, auth=Depends(machine)):
        scope(id, auth)
        return {"verified": store.attest(auth, body)}

    @app.get("/api/orgs/{tenant}/{kind}")
    def listing(tenant: str, kind: str, limit: int = 100, offset: int = 0, auth=Depends(session)):
        return store.list(auth["actor"], tenant, kind, limit, offset)

    root = web_root or Path(__file__).resolve().parents[3] / "releasefence-web/dist"
    if root.exists():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(root / "index.html")

    return app


def app_from_env():
    from .config import load_store

    store = load_store()
    actor = os.environ.get("RELEASEFENCE_USERNAME", "")
    password = os.environ.get("RELEASEFENCE_PASSWORD", "")
    if not actor or len(password) < 12 or password == "replace-me":
        raise RuntimeError("explicit ReleaseFence credentials required")
    with store.db() as db:
        exists = db.execute("SELECT 1 FROM users WHERE name=%s", (actor,)).fetchone()
    if not exists:
        store.create_user(actor, password)
    return create_app(
        store,
        origin=os.environ.get("RELEASEFENCE_ORIGIN", "http://127.0.0.1:8010"),
        administrator=actor,
        lab_loopback=os.environ.get("RELEASEFENCE_LAB_LOOPBACK") == "1",
    )
