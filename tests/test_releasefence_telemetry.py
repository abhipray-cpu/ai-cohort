import pytest
from contracts.releasefence import Span
from releasefence_api.telemetry import normalize_otlp, otlp


def test_otlp_redaction_parent_identity_and_export_roundtrip():
    spans = [
        Span(
            trace_id="1" * 32,
            span_id="2" * 16,
            name="PRIVATE PROMPT",
            release="a" * 64,
            started_ns=1,
            ended_ns=2,
        ),
        Span(
            trace_id="1" * 32,
            span_id="3" * 16,
            parent_span_id="2" * 16,
            name="tool",
            kind="tool",
            release="a" * 64,
            started_ns=1,
            ended_ns=2,
        ),
    ]
    body = otlp(spans)
    body["resourceSpans"][0]["resource"]["attributes"].append(
        {"key": "secret", "value": {"stringValue": "SECRET"}}
    )
    normalized = normalize_otlp(body)
    assert normalized[1].parent_span_id == "2" * 16
    assert normalized[0].trace_id == "1" * 32
    assert "PRIVATE" not in str(otlp(normalized)) and "SECRET" not in str(otlp(normalized))
    with pytest.raises(ValueError):
        normalize_otlp({"resourceSpans": []})


def test_real_otlp_protobuf_preserves_error_status_without_exception_payload():
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    from releasefence_api.telemetry import protobuf_payload

    message = ExportTraceServiceRequest()
    resource = message.resource_spans.add()
    attr = resource.resource.attributes.add()
    attr.key = "releasefence.release"
    attr.value.string_value = "a" * 64
    span = resource.scope_spans.add().spans.add(
        trace_id=bytes.fromhex("1" * 32),
        span_id=bytes.fromhex("2" * 16),
        name="PRIVATE ERROR",
        start_time_unix_nano=1,
        end_time_unix_nano=2,
    )
    span.status.code = 2
    span.status.message = "SECRET"
    normalized = normalize_otlp(protobuf_payload(message.SerializeToString()))
    assert normalized[0].status == "error"
    assert "PRIVATE" not in str(normalized) and "SECRET" not in str(normalized)
