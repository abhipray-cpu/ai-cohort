"""Customer-owned trace backends: export is not read-back verification."""

import base64
import json
import re
import uuid
from urllib.parse import quote

from contracts.releasefence import Span

from .network import request


def correlation(span):
    span = Span.model_validate(span)

    def run(id):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "releasefence:" + span.trace_id + ":" + id))

    return {
        "id": run(span.span_id),
        "parent": run(span.parent_span_id) if span.parent_span_id else None,
        "trace": str(uuid.uuid5(uuid.NAMESPACE_URL, "releasefence:" + span.trace_id)),
    }


def trace_gate(
    backends,
    scope,
    stable,
    candidate,
    start,
    end,
    now,
    *,
    backlog=None,
    profile="langsmith-phoenix-v1",
):
    profiles = {
        "langsmith-phoenix-v1": ("langsmith", "phoenix"),
        "mlflow-phoenix-v1": ("mlflow", "phoenix"),
    }
    if profile not in profiles:
        raise ValueError("unsupported trace qualification profile")
    issues = []
    for kind in profiles[profile]:
        if (backlog or {}).get(kind, 0):
            issues.append(kind + "_trace_export_incomplete")
        backend = next((b for b in backends if b["kind"] == kind and b["enabled"]), None)
        if not backend or backend["status"] != "verified":
            issues.append(kind + "_trace_backend_unverified")
            continue
        for release in (stable, candidate):
            proof = backend.get("verified_releases", {}).get(scope + ":" + release)
            if (
                not proof
                or not start <= proof["started_ns"] / 10**9 < end
                or not 0 <= now - proof["at"] <= 300
            ):
                issues.append(kind + "_release_window_readback_missing")
    return sorted(set(issues))


class Backend:
    def __init__(
        self, kind, export_url, read_url, key, project, *, transport=request, lab_loopback=False
    ):
        if kind not in {"langsmith", "phoenix", "mlflow"}:
            raise ValueError("unsupported trace backend")
        self.kind = kind
        self.export_url = export_url
        self.read_url = read_url.rstrip("/")
        self.project = project
        self.transport = transport
        self.lab = lab_loopback
        self.headers = {"Content-Type": "application/json"}
        if kind == "langsmith":
            self.headers.update({"x-api-key": key, "Langsmith-Project": project})
        elif kind == "mlflow":
            user, separator, password = key.partition(":")
            if (
                not user
                or not separator
                or not password
                or not re.fullmatch(r"[0-9]{1,20}", project)
            ):
                raise ValueError(
                    "MLflow requires scoped username:password and numeric experiment ID"
                )
            self.headers.update(
                {
                    "Authorization": "Basic " + base64.b64encode(key.encode()).decode(),
                    "x-mlflow-experiment-id": project,
                    "Content-Type": "application/x-protobuf",
                }
            )
        else:
            self.headers["Authorization"] = "Bearer " + key
            self.headers["x-project-name"] = project
            self.headers["Content-Type"] = "application/x-protobuf"

    def _request(self, url, *, body=None, method="POST"):
        status, raw = self.transport(
            url, body=body, headers=self.headers, method=method, lab_loopback=self.lab
        )
        if not 200 <= status < 300:
            raise ValueError("backend rejected request")
        return raw

    def export(self, spans):
        from .telemetry import otlp, protobuf_export

        raw = (
            protobuf_export(spans)
            if self.kind in {"phoenix", "mlflow"}
            else json.dumps(otlp(spans), separators=(",", ":")).encode()
        )
        self._request(self.export_url, body=raw)

    def verify(self, spans):
        spans = [Span.model_validate(s) for s in spans]
        if not spans or len(spans) > 100:
            raise ValueError("bounded nonempty evidence required")
        checked = []
        try:
            for span in spans:
                if self.kind == "langsmith":
                    ids = correlation(span)
                    item = json.loads(
                        self._request(self.read_url + "/runs/" + ids["id"], method="GET")
                    )
                    attrs = item.get("extra", {}).get("metadata", {})
                    ok = (
                        item.get("id") == ids["id"]
                        and item.get("parent_run_id") == ids["parent"]
                        and attrs.get("releasefence.release") == span.release
                        and attrs.get("releasefence.trace_id") == span.trace_id
                        and attrs.get("releasefence.span_id") == span.span_id
                    )
                elif self.kind == "mlflow":
                    trace = json.loads(
                        self._request(
                            self.read_url
                            + "/api/3.0/mlflow/traces/get?trace_id=tr-"
                            + span.trace_id,
                            method="GET",
                        )
                    ).get("trace", {})
                    info = trace.get("trace_info", {})
                    location = info.get("trace_location", {}).get("mlflow_experiment", {})

                    def id_bytes(value):
                        return base64.b64decode(value, validate=True).hex() if value else None

                    item = next(
                        (
                            r
                            for r in trace.get("spans", [])
                            if id_bytes(r.get("span_id")) == span.span_id
                        ),
                        {},
                    )
                    attrs = {
                        a["key"]: a.get("value", {}).get("string_value")
                        for a in item.get("attributes", [])
                    }
                    ok = (
                        info.get("trace_id") == "tr-" + span.trace_id
                        and location.get("experiment_id") == self.project
                        and id_bytes(item.get("trace_id")) == span.trace_id
                        and id_bytes(item.get("parent_span_id")) == span.parent_span_id
                        and attrs.get("releasefence.release") == span.release
                    )
                else:
                    url = (
                        self.read_url
                        + "/v1/projects/"
                        + quote(self.project, safe="")
                        + "/spans?trace_id="
                        + span.trace_id
                        + "&limit=100"
                    )
                    rows = json.loads(self._request(url, method="GET")).get("data", [])
                    item = next(
                        (r for r in rows if r.get("context", {}).get("span_id") == span.span_id), {}
                    )
                    ok = (
                        item.get("context", {}).get("trace_id") == span.trace_id
                        and (item.get("parent_id") or None) == span.parent_span_id
                        and item.get("attributes", {}).get("releasefence.release") == span.release
                    )
                if ok:
                    checked.append(span.span_id)
        except (ValueError, KeyError, TypeError, AttributeError, OSError):
            return {
                "verified": False,
                "checked": checked,
                "expected": len(spans),
                "reason": "readback_unavailable",
            }
        return {
            "verified": len(checked) == len(spans),
            "checked": checked,
            "expected": len(spans),
            "reason": None if len(checked) == len(spans) else "identity_mismatch",
        }
