import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from catalogbridge_api.ingest import parse_feed
from catalogbridge_api.matching import candidates, conflicts
from catalogbridge_api.store import Store
from contracts.catalogbridge import BatchSpec, Product, Usage
from pydantic import ValidationError


def test_contracts_reject_extra_fields_negative_usage_and_duplicate_models():
    with pytest.raises(ValidationError):
        Product(id="x", title="ok", cluster_id=3)
    with pytest.raises(ValidationError):
        Usage(input_tokens=-1, output_tokens=2)
    with pytest.raises(ValidationError):
        BatchSpec(master_id="a", supplier_id="b", economy_model="same", strong_model="same")


def test_feed_csv_json_preserve_literals_and_reject_duplicates_and_gold():
    rows = parse_feed(b'id,title,brand\na,"Crucial 8GB",Crucial\n', "csv")
    assert rows[0].title == "Crucial 8GB"
    with pytest.raises(ValueError, match="duplicate"):
        parse_feed(b"id,title\na,one\na,two\n", "csv")
    with pytest.raises(ValueError, match="forbidden"):
        parse_feed(json.dumps([{"id": "a", "title": "x", "label": 1}]).encode(), "json")


@pytest.mark.parametrize(
    "left,right",
    [
        ("8GB DDR4 SODIMM", "16GB DDR4 SODIMM"),
        ("8GB SODIMM", "8GB UDIMM"),
        ("2 pack mouse", "1 pack mouse"),
    ],
)
def test_variant_conflicts(left, right):
    assert conflicts(Product(id="l", title=left), Product(id="r", title=right))


def test_candidates_are_scoped_bounded_and_do_not_use_price_as_identity():
    query = Product(id="s", title="Crucial DDR4 8GB", brand="Crucial")
    rows = [Product(id=str(n), title="Crucial DDR4 8GB", price=str(n)) for n in range(15)]
    assert len(candidates(query, rows)) == 10
    assert not conflicts(query, rows[0])


def test_retrieval_normalizes_punctuation_and_keeps_single_candidate_for_assessment():
    query = Product(id="s", title="AB-123 USB-C")
    match = Product(id="m", title="AB123 USB C")
    assert candidates(query, [Product(id="d", title="USB cable"), match])[0].id == "m"
    assert candidates(Product(id="s", title="Zegarek"), [Product(id="m", title="Watch")])
    assert candidates(query, [match], limit=0) == []


def test_identity_constraints_ignore_marketing_specs_but_keep_title_variants():
    a = Product(id="a", title="LaCie 2TB Mobile Drive", brand="Ice-Watch")
    b = Product(
        id="b",
        title="LaCie 2TB Mobile Drive",
        brand="ICE WATCH",
        description="Range up to 5TB, 540MB per second. Can be used with new computers.",
    )
    assert not conflicts(a, b)
    assert "capacity" in conflicts(a, b.model_copy(update={"title": "LaCie 5TB Mobile Drive"}))
    assert "condition" in conflicts(
        Product(id="a", title="used camera"), Product(id="b", title="new camera")
    )


def setup_batch(tmp_path, tokens=1000):
    store = Store(tmp_path)
    master = store.import_feed("w", "master", [Product(id="m", title="Memory 8GB")])
    supplier = store.import_feed("w", "supplier", [Product(id="s", title="Memory 8GB")])
    batch = store.create_batch(
        "w",
        BatchSpec(
            master_id=master["id"],
            supplier_id=supplier["id"],
            token_budget=tokens,
            row_token_budget=tokens,
            egress=True,
        ),
    )
    return store, batch


def test_atomic_reservations_and_idempotent_settlement(tmp_path):
    store, batch = setup_batch(tmp_path)
    task = store.tasks("w", batch["id"])[0]

    def reserve(_):
        try:
            return store.reserve(batch["id"], task["id"], "economy", 600)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(item is not None for item in results) == 1
    attempt = next(x for x in results if x)
    usage = Usage(input_tokens=100, cached_input_tokens=20, output_tokens=50)
    store.settle(attempt, usage)
    store.settle(attempt, usage)
    metrics = store.analytics("w", batch["id"])
    assert metrics["tokens"] == 150 and metrics["reserved_tokens"] == 0
    assert metrics["attempts"] == 1
    with pytest.raises(ValueError, match="conflict"):
        store.settle(attempt, Usage(input_tokens=200, output_tokens=50))


def test_unknown_usage_holds_liability_and_restart_does_not_refund(tmp_path):
    store, batch = setup_batch(tmp_path)
    task = store.tasks("w", batch["id"])[0]
    attempt = store.reserve(batch["id"], task["id"], "economy", 700)
    store.settle(attempt, None)
    restarted = Store(tmp_path)
    assert restarted.analytics("w", batch["id"])["unknown_attempts"] == 1
    with pytest.raises(ValueError, match="unknown"):
        restarted.reserve(batch["id"], task["id"], "strong", 100)


def test_scoping_and_strict_budget_fail_closed(tmp_path):
    store, batch = setup_batch(tmp_path)
    with pytest.raises(KeyError):
        store.batch("other", batch["id"])
    with pytest.raises(ValueError, match="hard token"):
        store.create_batch(
            "w",
            BatchSpec(
                master_id=batch["spec"]["master_id"],
                supplier_id=batch["spec"]["supplier_id"],
                budget_mode="strict",
            ),
        )
