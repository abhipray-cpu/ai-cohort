import pytest
from contracts.catalogbridge import BatchSpec, Usage
from test_catalogbridge_core import setup_batch


def test_missing_journal_is_not_silently_recreated_as_healthy(tmp_path):
    store, b = setup_batch(tmp_path)
    store.journal.rename(store.journal.with_suffix(".lost"))
    from catalogbridge_api.store import Store

    reopened = Store(tmp_path)
    assert not reopened.analytics("w", b["id"])["journal_consistent"]


def test_restore_quarantine_blocks_dispatch_even_if_no_usage_discrepancy(tmp_path):
    store, b = setup_batch(tmp_path)
    with store.write() as db:
        db.execute("INSERT INTO meta VALUES('restore_quarantine','true')")
    task = store.tasks("w", b["id"])[0]
    with pytest.raises(ValueError, match="quarantine"):
        store.reserve(b["id"], task["id"], "economy", 100)


def test_per_model_reference_rates_and_cost_denominators(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    spec = BatchSpec.model_validate(
        b["spec"]
        | {
            "model_rates": {
                b["spec"]["economy_model"]: {
                    "id": "economy-test",
                    "basis": "reference_estimate",
                    "input_microunits_per_million": 1000000,
                    "output_microunits_per_million": 2000000,
                },
                b["spec"]["strong_model"]: {
                    "id": "strong-test",
                    "basis": "reference_estimate",
                    "input_microunits_per_million": 5000000,
                    "output_microunits_per_million": 10000000,
                },
            }
        }
    )
    with store.write() as db:
        db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), b["id"]))
    task = store.tasks("w", b["id"])[0]
    for route in ["economy", "strong"]:
        a = store.reserve(b["id"], task["id"], route, 100)
        store.settle(a, Usage(input_tokens=10, output_tokens=5))
    metrics = store.analytics("w", b["id"])
    assert metrics["estimated_microunits"] == 120
    assert metrics["cost_per_input_row_microunits"] == 120
    assert metrics["actual_charge"] is None


def test_repeated_start_cannot_duplicate_work(tmp_path):
    store, b = setup_batch(tmp_path)
    store.start("w", b["id"])
    with pytest.raises(ValueError):
        store.start("w", b["id"])
    assert len(store.tasks("w", b["id"])) == 1


def test_mixed_credit_and_reference_bases_cannot_be_aggregated(tmp_path):
    store, b = setup_batch(tmp_path, 30000)
    spec = BatchSpec.model_validate(
        b["spec"]
        | {
            "model_rates": {
                b["spec"]["economy_model"]: {"basis": "reference_estimate", "unit": "USD"},
                b["spec"]["strong_model"]: {"basis": "applicable_credit", "unit": "USD"},
            }
        }
    )
    with store.write() as db:
        db.execute("UPDATE batches SET spec=? WHERE id=?", (spec.model_dump_json(), b["id"]))
    task = store.tasks("w", b["id"])[0]
    for route in ["economy", "strong"]:
        a = store.reserve(b["id"], task["id"], route, 100)
        store.settle(a, Usage(input_tokens=10, output_tokens=5))
    assert store.analytics("w", b["id"])["estimated_microunits"] is None
