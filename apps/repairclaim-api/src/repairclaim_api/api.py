"""RepairClaim authenticated API and same-origin web application."""

import json
import os
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from contracts.repairclaim import Contract, Fact, Identifier, ShortText
from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import Field, SecretStr, StrictInt, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from repairclaim_api.errors import DomainError
from repairclaim_api.store import Store

BASE = "/api/repairclaim/v1"
COOKIE = "repairclaim_session"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


class BoundaryMiddleware:
    """Bound JSON before decoding, enforce write origins and protect every response."""

    def __init__(self, app, *, origin, store):
        self.app, self.origin = app, origin
        self.store = store

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def protected_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
                    ),
                ]
            await send(message)

        async def reject(code, status):
            await JSONResponse({"code": code}, status_code=status)(scope, receive, protected_send)

        if scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await self.app(scope, receive, protected_send)
        headers = scope.get("headers", [])
        origins = [value.decode("latin1") for key, value in headers if key.lower() == b"origin"]
        if origins != [self.origin]:
            return await reject("origin_denied", 403)
        if scope["path"] != BASE + "/sessions":
            from http.cookies import SimpleCookie

            cookie = SimpleCookie()
            try:
                for key, value in headers:
                    if key.lower() == b"cookie":
                        cookie.load(value.decode("latin1"))
                token = cookie[COOKIE].value if COOKIE in cookie else ""
                csrf = next(
                    (
                        value.decode("latin1")
                        for key, value in headers
                        if key.lower() == b"x-csrf-token"
                    ),
                    "",
                )
                self.store.check_csrf(token, csrf)
            except DomainError as error:
                return await reject(error.code, error.status)
        lengths = [value for key, value in headers if key.lower() == b"content-length"]
        if len(lengths) > 1 or (lengths and (len(lengths[0]) > 10 or not lengths[0].isdigit())):
            return await reject("invalid_content_length", 400)
        upload = scope["path"].startswith(BASE + "/cases/") and scope["path"].endswith("/documents")
        limit = 20 * 1024 * 1024 if upload else 65536
        if lengths and int(lengths[0]) > limit:
            return await reject("body_too_large", 413)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                return await reject("body_too_large", 413)
            if not message.get("more_body", False):
                break
        if body:
            content_types = [
                value.decode("latin1").split(";")[0].lower()
                for key, value in headers
                if key.lower() == b"content-type"
            ]
            if content_types != (["application/octet-stream"] if upload else ["application/json"]):
                return await reject("unsupported_media_type", 415)
            if not upload:
                try:
                    json.loads(
                        body,
                        object_pairs_hook=_unique,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError()),
                    )
                except (ValueError, RecursionError, UnicodeError):
                    return await reject("invalid_json", 422)
        sent = False

        async def replay_receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await self.app(scope, replay_receive, protected_send)


class Credentials(Contract):
    username: Annotated[str, Field(min_length=1, max_length=80)]
    password: Annotated[SecretStr, Field(min_length=1, max_length=256)]


class VehicleInput(Contract):
    make: ShortText
    model: ShortText
    model_year: Annotated[StrictInt, Field(ge=1980, le=2100)]
    jurisdiction: Literal["US", "IN", "CA", "GB"]


class CaseInput(Contract):
    vehicle_id: Identifier
    title: ShortText


class FactInput(Contract):
    expected_revision: Annotated[StrictInt, Field(ge=1)]
    facts: Annotated[tuple[Fact, ...], Field(max_length=100)]


class GrantInput(Contract):
    user_id: Identifier
    role: Literal["viewer", "editor"]
    ttl: Annotated[StrictInt, Field(gt=0, le=90 * 86400)] = 86400


def create_app(
    store: Store,
    *,
    public_origin: str,
    secure_cookies=True,
    parser=None,
    web_dir=None,
    codex_enabled=False,
    jev_enabled=False,
) -> FastAPI:
    parsed = urlsplit(public_origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or "*" in parsed.netloc
        or (
            parsed.scheme != "https"
            and (secure_cookies or parsed.hostname not in {"localhost", "127.0.0.1"})
        )
    ):
        raise ValueError("invalid REPAIRCLAIM_PUBLIC_ORIGIN")
    origin = public_origin.rstrip("/")
    app = FastAPI(title="RepairClaim", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[parsed.hostname])
    app.add_middleware(BoundaryMiddleware, origin=origin, store=store)

    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"code": error.code}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, error):
        return JSONResponse({"code": "validation_failed"}, status_code=422)

    @app.exception_handler(ValidationError)
    async def contract_error(request, error):
        return JSONResponse({"code": "validation_failed"}, status_code=422)

    def read_token(request: Request):
        token = request.cookies.get(COOKIE, "")
        store.authenticate(token)
        return token

    def write_token(request: Request):
        token = request.cookies.get(COOKIE, "")
        store.check_csrf(token, request.headers.get("x-csrf-token", ""))
        return token

    @app.get("/health/live")
    def live():
        return {"status": "alive", "stage": "implementation"}

    @app.get("/health/ready")
    def ready():
        with store._transaction() as db:
            heartbeat = db.execute(
                "SELECT value FROM rc_meta WHERE key='worker_heartbeat'"
            ).fetchone()
            parser_state = db.execute(
                "SELECT value FROM rc_meta WHERE key='parser_ready'"
            ).fetchone()
            quarantine = (
                db.execute("SELECT value FROM rc_meta WHERE key='quarantined'").fetchone()[0] == "1"
            )
        worker = bool(heartbeat and 0 <= store._now() - float(heartbeat[0]) < 240)
        parser_ok = bool(parser_state and parser_state[0] == "1")
        ok = worker and parser_ok and not quarantine
        return JSONResponse(
            {
                "status": "ready" if ok else "degraded",
                "worker": worker,
                "restricted_parser": parser_ok,
            },
            status_code=200 if ok else 503,
        )

    @app.post(f"{BASE}/sessions")
    def login(body: Credentials, response: Response):
        session = store.login(body.username, body.password.get_secret_value())
        response.set_cookie(
            COOKIE,
            session.token,
            max_age=8 * 3600,
            httponly=True,
            secure=secure_cookies,
            samesite="strict",
            path=BASE,
        )
        return {"csrf_token": session.csrf_token, "expires_at": session.expires_at}

    @app.delete(f"{BASE}/sessions/current", status_code=204)
    def logout(response: Response, token: str = Depends(write_token)):
        store.logout(token)
        response.delete_cookie(
            COOKIE, path=BASE, secure=secure_cookies, httponly=True, samesite="strict"
        )

    @app.get(f"{BASE}/me")
    def me(token: str = Depends(read_token)):
        return {**store.authenticate(token), "csrf_token": store.csrf_token(token)}

    @app.post(f"{BASE}/vehicles", status_code=201)
    def vehicle(body: VehicleInput, token: str = Depends(write_token)):
        return store.create_vehicle(token, **body.model_dump())

    @app.get(f"{BASE}/cases")
    def cases(token: str = Depends(read_token)):
        return store.list_cases(token)

    @app.post(f"{BASE}/cases", status_code=201)
    def new_case(body: CaseInput, token: str = Depends(write_token)):
        return store.create_case(token, body.vehicle_id, body.title)

    @app.get(f"{BASE}/cases/{{case_id}}")
    def case(case_id: Identifier, token: str = Depends(read_token)):
        return store.get_case(token, case_id)

    @app.get(f"{BASE}/cases/{{case_id}}/snapshot")
    def snapshot(case_id: Identifier, token: str = Depends(read_token)):
        return store.snapshot(token, case_id)

    @app.post(f"{BASE}/cases/{{case_id}}/fact-revisions")
    def facts(case_id: Identifier, body: FactInput, token: str = Depends(write_token)):
        return store.replace_facts(token, case_id, body.expected_revision, body.facts)

    @app.get(f"{BASE}/cases/{{case_id}}/timeline")
    def timeline(case_id: Identifier, token: str = Depends(read_token)):
        return store.timeline(token, case_id)

    @app.post(f"{BASE}/cases/{{case_id}}/grants", status_code=201)
    def grant(case_id: Identifier, body: GrantInput, token: str = Depends(write_token)):
        store.grant(token, case_id, body.user_id, body.role, ttl=body.ttl)
        return {"status": "granted"}

    @app.delete(f"{BASE}/cases/{{case_id}}/grants/{{user_id}}", status_code=204)
    def revoke(case_id: Identifier, user_id: Identifier, token: str = Depends(write_token)):
        store.revoke_grant(token, case_id, user_id)

    @app.delete(f"{BASE}/cases/{{case_id}}", status_code=204)
    def delete(
        case_id: Identifier,
        if_match: Annotated[int, Header(ge=1)],
        token: str = Depends(write_token),
    ):
        store.delete_case(token, case_id, if_match)

    from repairclaim_api.parser import RestrictedParser
    from repairclaim_api.routes import register_routes

    register_routes(
        app,
        store,
        read_token,
        write_token,
        parser or RestrictedParser(),
        codex_enabled=codex_enabled,
        jev_enabled=jev_enabled,
    )
    if web_dir is not None:
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


def app_from_env():
    root = os.environ.get("REPAIRCLAIM_DATA_DIR")
    origin = os.environ.get("REPAIRCLAIM_PUBLIC_ORIGIN")
    if not root or not origin:
        raise ValueError("Set explicit REPAIRCLAIM_DATA_DIR and REPAIRCLAIM_PUBLIC_ORIGIN")
    from repairclaim_api.parser import RestrictedParser

    web = Path(__file__).resolve().parents[3] / "repairclaim-web" / "dist"
    return create_app(
        Store(Path(root) / "repairclaim.sqlite3"),
        public_origin=origin,
        secure_cookies=not origin.startswith(("http://127.0.0.1", "http://localhost")),
        web_dir=web if web.is_dir() else None,
        parser=RestrictedParser(
            mode=os.environ.get("REPAIRCLAIM_PARSER", "auto"),
            engine=os.environ.get("REPAIRCLAIM_CONTAINER_ENGINE", "docker"),
        ),
        codex_enabled=os.environ.get("REPAIRCLAIM_ENABLE_CODEX") == "1",
        jev_enabled=os.environ.get("REPAIRCLAIM_ENABLE_JEV") == "1",
    )
