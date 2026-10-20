import hashlib
import json
import time

import pytest
from casecouncil_api.evaluation import audit_corpus, campaign
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import CONTEXT


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "corpus"
    (root / "inputs").mkdir(parents=True)
    (root / "gold").mkdir()
    raw = b"Personally authored fixture: policy and service need separate consideration."
    (root / "inputs/policy.txt").write_bytes(raw)
    (root / "gold/case.json").write_text(
        json.dumps(
            {"issues": {"premium": "partial_uphold"}, "canary": "EVALUATOR_SECRET_OUTCOME_1847"}
        )
    )
    value = {
        "schema_version": 1,
        "permission": {
            "basis": "owned_test",
            "reference": "Personally authored evaluation engineering material",
            "expires": time.time() + 86400,
            "egress": True,
        },
        "cases": [
            {
                "id": "opaque_001",
                "group": "independent_001",
                "split": "development",
                "cohort": "authored_fixture",
                "context": CONTEXT,
                "documents": [
                    {
                        "path": "inputs/policy.txt",
                        "kind": "policy",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
                "gold_path": "gold/case.json",
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(value))
    return root


def test_acquisition_paths_and_hashes_fail_closed(corpus):
    assert audit_corpus(corpus)["cases"] == 1
    p = corpus / "manifest.json"
    m = json.loads(p.read_text())
    m["cases"][0]["documents"][0]["path"] = "../private.txt"
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        audit_corpus(corpus)


def test_owned_fixture_campaign_keeps_gold_out_of_all_prompts(corpus, tmp_path):
    provider = ControlledProvider()
    report = campaign(
        corpus,
        tmp_path / "campaign",
        provider,
        "debate",
        1,
        22,
        "Explicit authored-fixture authority and egress approval",
    )
    assert report["completed"] == 1 and report["calls"] == 8
    assert report["full_product_accepted"] is False and report["real_data_validated"] is False
    assert all("EVALUATOR_SECRET_OUTCOME_1847" not in json.dumps(p) for p in provider.prompts)


def test_rights_expiry_is_not_bypassed_by_live_flag(corpus):
    p = corpus / "manifest.json"
    m = json.loads(p.read_text())
    m["permission"]["expires"] = 0
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        audit_corpus(corpus)


def test_offline_inventory_does_not_imply_model_egress_approval(corpus, tmp_path):
    path = corpus / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["permission"]["egress"] = False
    path.write_text(json.dumps(manifest))
    assert audit_corpus(corpus)["model_egress_approved"] is False
    provider = ControlledProvider()
    with pytest.raises(ValueError):
        campaign(
            corpus,
            tmp_path / "forbidden",
            provider,
            "debate",
            1,
            22,
            "Source licence alone is not explicit model-egress approval",
        )
    assert provider.prompts == []


def test_approval_creates_only_a_bounded_development_subset_without_mutating_source(
    corpus, tmp_path
):
    from casecouncil_api.evaluation import approve_development_subset

    original = (corpus / "manifest.json").read_bytes()
    target = tmp_path / "approved"
    receipt = approve_development_subset(
        corpus,
        target,
        1,
        22,
        "User explicitly approved prepared excerpts to configured Codex model service",
    )
    approved = json.loads((target / "manifest.json").read_text())
    assert receipt["max_calls"] == 22 and len(approved["cases"]) == 1
    assert approved["permission"]["egress"] is True
    assert audit_corpus(target)["cases"] == 1
    assert (corpus / "manifest.json").read_bytes() == original
    with pytest.raises(ValueError):
        approve_development_subset(
            corpus,
            tmp_path / "too-many",
            7,
            154,
            "User approved only six development cases and at most 132 calls",
        )


@pytest.mark.parametrize("mode,calls", [("single", 2), ("vote_only", 7), ("single_refine", 11)])
def test_baselines_exercise_the_real_pipeline_without_gold_leakage(corpus, tmp_path, mode, calls):
    provider = ControlledProvider()
    report = campaign(
        corpus,
        tmp_path / mode,
        provider,
        mode,
        1,
        22,
        "Explicit authored-fixture authority and egress approval",
    )
    assert report["completed"] == 1 and report["calls"] == calls
    assert not report["real_data_validated"]
    assert all("EVALUATOR_SECRET_OUTCOME_1847" not in json.dumps(p) for p in provider.prompts)
