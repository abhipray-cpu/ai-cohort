from collections import deque

import pytest
from agent_core.orchestrator import ExtractionFailed, ExtractionOrchestrator
from agent_core.provider import StructuredGeneration
from contracts.tenderlens import PageLookupResult


class FakeProvider:
    def __init__(self, responses):
        self.responses = deque(responses)
        self.prompts = []

    def generate(self, *, prompt, schema):
        self.prompts.append(prompt)
        return StructuredGeneration(text=self.responses.popleft(), exit_code=0, elapsed_ms=10)


class FakePageLookup:
    def lookup(self, request):
        return PageLookupResult(
            document_id=request.document_id, page=request.page, text="Deadline 1 Dec 2026"
        )


class BadPageLookup:
    def lookup(self, request):
        return {"document_id": request.document_id, "page": 0, "text": "bad"}


def valid_brief():
    return '{"schema_version":"1.0","title":"Road works","claims":[{"kind":"deadline","value":"1 Dec 2026","status":"verified","citations":[{"document_id":"d1","page":1,"quote":"Deadline 1 Dec 2026"}]}],"open_questions":[]}'


def test_parse_failure_is_logged_and_repaired():
    provider = FakeProvider(["not json", valid_brief()])
    events = []
    result = ExtractionOrchestrator(provider, FakePageLookup(), events.append).run(
        run_id="run-1", pages=[("d1", 1)], prompt="Extract"
    )
    assert result.claims[0].value == "1 Dec 2026"
    assert len(provider.prompts) == 2
    assert "validation" in provider.prompts[1].lower()
    assert events[0].stage == "parse"


def test_exhausted_retries_are_terminal():
    provider = FakeProvider(["bad", "bad", "bad"])
    events = []
    with pytest.raises(ExtractionFailed):
        ExtractionOrchestrator(provider, FakePageLookup(), events.append).run(
            run_id="run-2", pages=[("d1", 1)], prompt="Extract"
        )
    assert len(provider.prompts) == 3
    assert len(events) == 3


def test_invalid_tool_result_is_rejected_before_model_call():
    provider = FakeProvider([valid_brief()])
    events = []
    with pytest.raises(ExtractionFailed):
        ExtractionOrchestrator(provider, BadPageLookup(), events.append).run(
            run_id="run-3", pages=[("d1", 1)], prompt="Extract"
        )
    assert not provider.prompts
    assert events[0].stage == "tool_response"


def test_citation_quote_must_match_page():
    provider = FakeProvider([valid_brief(), valid_brief(), valid_brief()])
    events = []

    class DifferentPageLookup:
        def lookup(self, request):
            return PageLookupResult(
                document_id=request.document_id, page=request.page, text="No deadline here"
            )

    with pytest.raises(ExtractionFailed):
        ExtractionOrchestrator(provider, DifferentPageLookup(), events.append).run(
            run_id="run-4", pages=[("d1", 1)], prompt="Extract"
        )
    assert events[0].stage == "evidence"


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("ERROR: Selected model is at capacity.", "capacity unavailable"),
        ("Usage limit reached", "usage limit reached"),
    ],
)
def test_provider_operational_failure_is_actionable_and_logged(stderr, expected):
    class ExitProvider:
        def generate(self, *, prompt, schema):
            return StructuredGeneration(text="", exit_code=1, elapsed_ms=12, stderr=stderr)

    events = []
    with pytest.raises(ExtractionFailed, match=expected):
        ExtractionOrchestrator(ExitProvider(), FakePageLookup(), events.append).run(
            run_id="run-5", pages=[("d1", 1)], prompt="Extract"
        )
    assert len(events) == 1
    assert events[0].stage == "provider"
    assert expected in events[0].error_summary
