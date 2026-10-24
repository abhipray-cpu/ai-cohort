"""Public record minimization must not manufacture repair evidence or expose identities."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "rc_complaints", Path(__file__).parents[1] / "scripts/repairclaim_complaints.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_public_record_keeps_only_vehicle_metadata_not_private_or_inferred_facts():
    raw = {
        "odiNumber": "12345678",
        "vin": "PRIVATEVIN",
        "summary": "My address and a reported repair date",
        "dateOfIncident": "2024-01-01",
        "dateComplaintFiled": "2024-03-01",
        "components": "ENGINE",
        "products": [{"type": "Vehicle", "make": "HONDA", "model": "CR-V", "productYear": "2017"}],
    }
    result = module.minimize(raw, ("CR-V", 2017))
    assert result["facts"] == {"model": "CR-V", "model_year": 2017}
    assert "PRIVATEVIN" not in str(result)
    assert "summary" not in result
    assert "repair_date" not in result["facts"]
    assert "in_service_date" not in result["facts"]
    assert result["record_type"] == "public_unverified_consumer_complaint_metadata"


def test_wrong_or_missing_product_identity_is_excluded_not_replaced_from_query():
    assert module.minimize({"odiNumber": "123", "products": []}, ("CR-V", 2017)) is None
    assert (
        module.minimize(
            {
                "odiNumber": "123",
                "products": [{"make": "HONDA", "model": "HR-V", "productYear": "2017"}],
            },
            ("CR-V", 2017),
        )
        is None
    )


def test_actual_nhtsa_product_field_names_are_supported_without_query_fallback():
    raw = {
        "odiNumber": "12345678",
        "products": [
            {
                "type": "Vehicle",
                "productMake": "HONDA",
                "productModel": "CR-V",
                "productYear": "2017",
            }
        ],
    }
    result = module.minimize(raw, ("CR-V", 2017))
    assert result is not None
    assert result["facts"] == {"model": "CR-V", "model_year": 2017}


def test_metadata_scenarios_do_not_promote_absence_to_coverage_labels():
    import pytest

    spec = importlib.util.spec_from_file_location(
        "rc_http_replay", Path(__file__).parents[1] / "scripts/repairclaim_public_e2e.py"
    )
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    record = module.minimize(
        {
            "odiNumber": "123",
            "products": [{"productMake": "HONDA", "productModel": "CR-V", "productYear": "2017"}],
        },
        ("CR-V", 2017),
    )
    result = replay.public_record_scenarios([record], replay.SPECS[3])
    assert result[0][2] == "missing_evidence"
    with pytest.raises(ValueError):
        replay.public_record_scenarios([record, record], replay.SPECS[3])
    record["facts"]["repair_date"] = "2020-01-01"
    with pytest.raises(ValueError):
        replay.public_record_scenarios([record], replay.SPECS[3])


def test_repair_document_track_preserves_make_and_does_not_invent_payment():
    spec = importlib.util.spec_from_file_location(
        "rc_document_replay", Path(__file__).parents[1] / "scripts/repairclaim_public_e2e.py"
    )
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    scenarios = replay.repair_document_scenarios()
    assert len(scenarios) == 7
    assert scenarios[-1][1]["make"] == "Kia"
    assert scenarios[-1][1]["model"] == "Sportage"
    assert all("paid_amount" not in facts for _, facts, _ in scenarios)
    assert all(expected == "appears_outside_conditions" for _, _, expected in scenarios[:-1])
    assert scenarios[-1][2] is None  # unsupported make, not a negative coverage verdict
