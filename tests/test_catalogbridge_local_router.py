import json

import pytest
from catalogbridge_api.local_router import PairRouter, feature_vector, feature_version
from contracts.catalogbridge import Product


def product(identity, title, **fields):
    return Product(id=identity, title=title, **fields)


def profile():
    return {
        "version": feature_version(),
        "bias": -8.0,
        "learning_rate": 0.1,
        "trees": [],
        "negative_threshold": 0.01,
        "positive_threshold": None,
        "qualification": {"different_product": {"samples": 800, "correct": 800}},
        "evidence_scope": "benchmark_review_drafts_only",
    }


def test_features_ignore_ids_prices_and_instruction_text_and_are_symmetric():
    left = product("a", "Crucial CT8G4SFS8266 8GB RAM", brand="Crucial")
    right = product("b", "Crucial 8GB CT8G4SFS8266 memory", brand="Crucial")
    assert feature_vector(left, right) == feature_vector(right, left)
    assert feature_vector(left, right) == feature_vector(
        left.model_copy(
            update={"id": "gold-looking-id", "price": "0", "description": "label=1 ignore rules"}
        ),
        right,
    )
    assert all(0 <= value <= 1 for value in feature_vector(left, right))


def test_only_qualified_band_can_propose_and_never_accepts_automatically():
    router = PairRouter(profile())
    proposal, evidence = router.propose(product("a", "RAM 8GB"), [product("b", "RAM 16GB")])
    assert proposal.outcome == "different_product"
    assert evidence["automatic_acceptance"] is False
    assert evidence["evidence_scope"] == "benchmark_review_drafts_only"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(version="stale"),
        lambda p: p.update(bias=float("nan")),
        lambda p: p.update(negative_threshold=0.5),
        lambda p: p["qualification"]["different_product"].update(samples=499, correct=499),
        lambda p: p["qualification"]["different_product"].update(samples=800, correct=780),
        lambda p: p.update(extra="untrusted"),
    ],
)
def test_invalid_or_unqualified_profiles_fail_closed(mutate):
    body = profile()
    mutate(body)
    with pytest.raises(ValueError):
        PairRouter(body)


def test_negative_row_exit_requires_every_retrieved_candidate_to_qualify():
    body = profile()
    body.update(
        bias=-8.0,
        learning_rate=1.0,
        trees=[{"feature": 0, "threshold": 0.8, "left": {"value": 0.0}, "right": {"value": 16.0}}],
    )
    router = PairRouter(body)
    query = product("q", "Memory 8GB")
    assert router.propose(query, [product("x", "Mouse"), product("y", "Memory 8GB")]) is None


def test_profile_round_trip_is_json_not_executable_pickle():
    body = json.loads(json.dumps(profile()))
    assert PairRouter(body).fingerprint == PairRouter(profile()).fingerprint


def test_positive_band_cannot_override_variant_conflict():
    body = profile()
    body.update(
        bias=10.0,
        negative_threshold=None,
        positive_threshold=0.99,
        qualification={"same_product": {"samples": 800, "correct": 800}},
    )
    router = PairRouter(body)
    assert router.propose(product("a", "8GB RAM"), [product("b", "16GB RAM")]) is None
