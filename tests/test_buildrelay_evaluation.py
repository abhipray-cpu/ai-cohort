import io
import zipfile

from buildrelay_api.evaluation import normalized, overlap
from buildrelay_api.github import MAX_EVIDENCE_CHARS, select_archive
from buildrelay_api.workflow import triage_evidence
from test_buildrelay_workflow import Provider


def pack_logs(files):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return raw.getvalue()


def test_selector_keeps_middle_failure_and_context_after_long_cleanup():
    lines = ["normal build output " * 5] * 700
    lines[300:303] = [
        "running customer test",
        "AssertionError: expected revenue 42",
        "at test_invoice.py:17",
    ]
    archive = pack_logs({"job.log": "\n".join(lines)})
    evidence = select_archive(archive, "source")
    assert "AssertionError: expected revenue 42" in evidence["text"]
    assert "running customer test" in evidence["text"]
    assert "at test_invoice.py:17" in evidence["text"]
    assert evidence["truncated"]
    assert len(evidence["text"]) <= MAX_EVIDENCE_CHARS
    assert evidence == select_archive(archive, "source")


def test_selector_prioritizes_failed_file_over_alphabetical_success_noise():
    files = {f"a-{n}.log": "successful checkout\n" * 1000 for n in range(15)}
    files["z-failed.log"] = (
        "setup\n" * 2000
        + "fatal: deployment certificate expired\ntrace detail\n"
        + "cleanup\n" * 2000
    )
    evidence = select_archive(pack_logs(files), "source")
    assert "fatal: deployment certificate expired" in evidence["text"]
    assert len(evidence["text"]) <= MAX_EVIDENCE_CHARS


def test_selector_preserves_complete_small_logs_and_redacts_secrets():
    evidence = select_archive(
        pack_logs({"job.log": "setup\nerror: secret-value\ncleanup"}), "source", ["secret-value"]
    )
    assert evidence["text"] == "FILE: job.log\nsetup\nerror: [REDACTED]\ncleanup\n"
    assert not evidence["truncated"]


def test_omitted_unsafe_and_oversized_members_mark_coverage_partial():
    evidence = select_archive(
        pack_logs(
            {"../escape.log": "failure", "huge.log": "x" * 4_000_001, "safe.log": "error: genuine"}
        ),
        "source",
    )
    assert evidence["truncated"]
    assert "genuine" in evidence["text"] and "escape.log" not in evidence["text"]


def test_selected_windows_have_truthful_redacted_line_provenance():
    from buildrelay_api.workflow import redact

    text = "ordinary line\n" * 6000 + "AssertionError: genuine failure\n" + "cleanup\n" * 6000
    evidence = select_archive(pack_logs({"job.log": text}), "source")
    assert evidence["spans"]
    source_lines = redact(text).splitlines()
    for span in evidence["spans"]:
        expected = "\n".join(source_lines[span["redacted_start"] - 1 : span["redacted_end"]])
        assert expected in evidence["text"]
    assert len(evidence["text"]) <= MAX_EVIDENCE_CHARS


def test_analysis_requests_initiating_diagnostic_not_only_terminal_status():
    class CaptureProvider(Provider):
        def generate(self, **kwargs):
            self.prompt = kwargs["prompt"]
            return super().generate(**kwargs)

    import json

    from test_buildrelay_workflow import triage

    provider = CaptureProvider([json.dumps(triage())])
    result = triage_evidence(
        provider, {}, {"text": "setup\nAssertionError: expected 2, got 3\nexit 1"}, lambda *_: None
    )
    assert result["citations"][0]["line"] == 2
    assert "initiating diagnostic" in provider.prompt


def test_gold_comparison_normalizes_annotation_ansi_artifacts_without_changing_evidence():
    assert (
        normalized("[0m[[0m[31merror[0m] 2 of 17 test tasks failed:[0m")
        == "[error] 2 of 17 test tasks failed:"
    )
    assert overlap(
        {"citations": [{"quote": "[error] 2 of 17 test tasks failed:"}]},
        "[0m[[0m[31merror[0m] 2 of 17 test tasks failed:[0m",
    )


def test_pure_evaluation_ports_use_same_selector_and_analysis_without_fake_run_identity():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as archive:
        archive.writestr("job.log", "Test checkout\nAssertionError: expected 2, got 3")
    evidence = select_archive(raw.getvalue(), "https://zenodo.org/records/3632351")
    assert evidence["source"] == "https://zenodo.org/records/3632351"
    notes = []
    # FILE header shifts citation to line 3; use a deliberately grounded response.
    import json

    from test_buildrelay_workflow import triage

    value = triage()
    value["citations"][0]["line"] = 3
    result = triage_evidence(
        Provider([json.dumps(value)]),
        {"provider": "Travis", "build_id": "original-source-id"},
        evidence,
        lambda action, detail: notes.append((action, detail)),
    )
    assert result["confidence"] == 0.8
    assert notes[0][0] == "generation_started"
