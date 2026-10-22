"""Customer-side HTTP bundle adapter. Raw task payloads never enter telemetry."""

import hmac
import json
import os
from pathlib import Path
from typing import Annotated, Literal

from contracts.releasefence import Contract, Digest, Identifier, Release, Usage
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field, StrictInt

from .core import digest
from .network import request, resolve_destination
from .sdk import Runtime, Spool


class TaskInput(Contract):
    id: Identifier
    session: Identifier
    input: Annotated[str, Field(max_length=10000)]


class TaskResult(Contract):
    release: Digest
    output: Annotated[str, Field(max_length=20000)]
    outcome: Literal["success", "failure", "abstained", "manual_required", "unknown"]
    model_calls: Annotated[StrictInt, Field(ge=0, le=1000)]
    usage: Annotated[list[Usage], Field(max_length=100)] = Field(default_factory=list)
    stop_reason: Literal["complete", "iteration_exhausted", "deadline", "schema_exhausted"] = (
        "complete"
    )


class HTTPBundles:
    def __init__(self, values, *, transport=request, lab_loopback=False):
        if not values or len(values) > 256:
            raise ValueError("finite bundle registry required")
        self.values = values
        self.transport = transport
        self.lab = lab_loopback
        for identity, config in values.items():
            if digest(Release.model_validate(config["manifest"])) != identity:
                raise ValueError("manifest identity mismatch")
            resolve_destination(config["url"], lab_loopback=lab_loopback)
            if not 1 <= len(config["token"]) <= 512:
                raise ValueError("bundle credential required")
            timeout = config.get("timeout_seconds", 300)
            if type(timeout) is not int or not 10 <= timeout <= 3600:
                raise ValueError("bounded task deadline required")

    def call(self, release, path, body, *, task=False):
        config = self.values[release]
        timeout = config.get("timeout_seconds", 300) if task else 5
        status, raw = self.transport(
            config["url"].rstrip("/") + path,
            body=json.dumps(body, separators=(",", ":")).encode(),
            headers={"Authorization": "Bearer " + config["token"]},
            lab_loopback=self.lab,
            timeout_seconds=timeout,
            deadline_seconds=timeout if task else 10,
        )
        if not 200 <= status < 300:
            raise OSError("bundle unavailable")
        return json.loads(raw)

    def probe(self, release, nonce):
        result = self.call(release, "/releasefence/v1/probe", {"release": release, "nonce": nonce})
        if (
            result.get("nonce") != nonce
            or result.get("release") != release
            or result.get("healthy") is not True
        ):
            raise ValueError("loaded bundle probe failed")
        return digest({"release": release, "nonce": nonce, "healthy": True})

    def invoke(self, release, task):
        result = TaskResult.model_validate(
            self.call(
                release,
                "/releasefence/v1/tasks",
                {**task.model_dump(), "release": release},
                task=True,
            )
        )
        if result.release != release or result.model_calls < len(
            {u.attempt for u in result.usage if not u.inclusive}
        ):
            raise ValueError("bundle response contract mismatch")
        return result


def create_gateway(router, spool, bundles, token):
    if len(token) < 12:
        raise ValueError("explicit gateway credential required")
    runtime = Runtime(router, spool)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def bounded(request, call_next):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse({"detail": "task body too large"}, 413)
        request._body = bytes(body)
        return await call_next(request)

    @app.get("/health/live")
    def live():
        return {"live": True}

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({"detail": "invalid bounded task contract"}, 422)

    @app.post("/agent/v1/tasks")
    def run(body: TaskInput, request: Request):
        if not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
            raise HTTPException(403, "scoped credential required")
        try:
            with runtime.task(body.id, body.session) as task:
                # An unavailable remote outcome is not recorded as free inference.
                task.model_attempt("unknown:" + body.id)
                result = bundles.invoke(task.release, body)
                if result.stop_reason != "complete" and result.outcome == "success":
                    result = result.model_copy(update={"outcome": "failure"})
                task.declared_model_calls = result.model_calls
                for usage in result.usage:
                    task.emit("usage", usage=usage)
                task.outcome = result.outcome
                task.stop_reason = result.stop_reason
            return result.model_dump(mode="json")
        except (OSError, ValueError, KeyError):
            raise HTTPException(503, "bundle dispatch or evidence unavailable") from None

    return app


def app_from_env():
    from .connector import Router
    from .crypto import private_key

    config = json.loads(Path(os.environ["RELEASEFENCE_CONNECTOR_CONFIG"]).read_text())
    for item in config["bundle_endpoints"].values():
        item["token"] = os.environ[item["token_env"]]
    bundles = HTTPBundles(
        config["bundle_endpoints"], lab_loopback=config.get("lab_loopback", False)
    )
    root = Path(config["data_dir"])
    root.mkdir(parents=True, exist_ok=True)
    router = Router(
        root / "router.db",
        config["enrollment"],
        config["application"],
        config["environment"],
        config["server_public_key"],
        private_key(os.environ["RELEASEFENCE_RUNTIME_SIGNING_KEY"]),
        set(bundles.values),
        config["stable"],
        probe=bundles.probe,
    )
    return create_gateway(
        router, Spool(root / "events.db"), bundles, os.environ["RELEASEFENCE_GATEWAY_TOKEN"]
    )
