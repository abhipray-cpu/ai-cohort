"""Privacy-minimal OTLP mapping and explicit customer-side instrumentation."""

from contracts.releasefence import Span


def attributes(values):
    if len(values) > 128:
        raise ValueError("too many attributes")
    return {
        v["key"]: v.get("value", {}).get("stringValue")
        for v in values
        if isinstance(v, dict) and isinstance(v.get("key"), str)
    }


def normalize_otlp(payload):
    if not isinstance(payload, dict) or set(payload) - {"resourceSpans"}:
        raise ValueError("unsupported OTLP envelope")
    output = []
    for resource in payload.get("resourceSpans", []):
        attrs = attributes(resource.get("resource", {}).get("attributes", []))
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                values = attributes(span.get("attributes", []))
                release = values.get("releasefence.release") or attrs.get("releasefence.release")
                kind = (values.get("openinference.span.kind") or "agent").lower()
                if kind not in {"agent", "llm", "tool", "retriever"}:
                    kind = "agent"
                output.append(
                    Span(
                        trace_id=span["traceId"],
                        span_id=span["spanId"],
                        parent_span_id=span.get("parentSpanId") or None,
                        name=kind,
                        kind=kind,
                        release=release,
                        started_ns=int(span["startTimeUnixNano"]),
                        ended_ns=int(span["endTimeUnixNano"]),
                        status={1: "ok", 2: "error"}.get(
                            span.get("status", {}).get("code", 0), "unset"
                        ),
                    )
                )
                if len(output) > 100:
                    raise ValueError("too many spans")
    if not output:
        raise ValueError("no supported spans")
    return output


def otlp(spans):
    from .backends import correlation

    result = []
    for value in spans:
        s = Span.model_validate(value)
        item = {
            "traceId": s.trace_id,
            "spanId": s.span_id,
            "name": s.kind,
            "startTimeUnixNano": str(s.started_ns),
            "endTimeUnixNano": str(s.ended_ns),
            "attributes": [
                {"key": "releasefence.release", "value": {"stringValue": s.release}},
                {"key": "openinference.span.kind", "value": {"stringValue": s.kind.upper()}},
            ],
            "status": {"code": {"unset": 0, "ok": 1, "error": 2}[s.status]},
        }
        if s.parent_span_id:
            item["parentSpanId"] = s.parent_span_id
        ids = correlation(s)
        metadata = {
            "langsmith.trace.id": ids["trace"],
            "langsmith.span.id": ids["id"],
            "langsmith.metadata.releasefence.release": s.release,
            "langsmith.metadata.releasefence.trace_id": s.trace_id,
            "langsmith.metadata.releasefence.span_id": s.span_id,
        }
        if ids["parent"]:
            metadata["langsmith.span.parent_id"] = ids["parent"]
        item["attributes"].extend(
            {"key": k, "value": {"stringValue": v}} for k, v in metadata.items()
        )
        result.append(item)
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": "releasefence-enrolled-agent"},
                        }
                    ]
                },
                "scopeSpans": [{"scope": {"name": "releasefence"}, "spans": result}],
            }
        ]
    }


def protobuf_payload(raw):
    import base64

    from google.protobuf.json_format import MessageToDict
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    request = ExportTraceServiceRequest()
    request.ParseFromString(raw)
    value = MessageToDict(request, use_integers_for_enums=True)
    for resource in value.get("resourceSpans", []):
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                for key in ("traceId", "spanId", "parentSpanId"):
                    if span.get(key):
                        span[key] = base64.b64decode(span[key], validate=True).hex()
    return value


def protobuf_export(spans):
    """OTLP's protobuf JSON mapping uses base64 bytes, not hexadecimal IDs."""
    import base64

    from google.protobuf.json_format import ParseDict
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    value = otlp(spans)
    for resource in value["resourceSpans"]:
        for scope in resource["scopeSpans"]:
            for span in scope["spans"]:
                for key in ("traceId", "spanId", "parentSpanId"):
                    if span.get(key):
                        span[key] = base64.b64encode(bytes.fromhex(span[key])).decode()
    return ParseDict(value, ExportTraceServiceRequest()).SerializeToString()


class TraceBridge:
    """A dedicated tracer provider avoids changing the application's global provider."""

    def __init__(self, endpoint, headers, release, *, exporter=None):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        self.provider = TracerProvider(
            resource=Resource(
                {"service.name": "releasefence-enrolled-agent", "releasefence.release": release}
            )
        )
        self.provider.add_span_processor(
            BatchSpanProcessor(
                exporter or OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=5),
                max_queue_size=1024,
                max_export_batch_size=100,
            )
        )
        self.tracer = self.provider.get_tracer("releasefence")

    def span(self, kind="agent"):
        if kind not in {"agent", "llm", "tool", "retriever"}:
            raise ValueError("unsupported span kind")
        return self.tracer.start_as_current_span(
            kind, attributes={"openinference.span.kind": kind.upper()}, record_exception=False
        )

    def shutdown(self):
        self.provider.force_flush(timeout_millis=10000)
        self.provider.shutdown()
