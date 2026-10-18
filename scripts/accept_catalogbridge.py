"""Fail-closed current release gate; engineering is not production acceptance."""

import json


def main():
    report = {
        "verdict": "blocked",
        "mandatory_open_gates": [
            "Historical unknown liabilities require authoritative reconciliation, not owner acknowledgement",
            "Strict hard-token enforcement unavailable on installed CLI",
            "Effective model identities are absent from observed runtime telemetry",
            "Independent held-out calibration/adjudication and paired quality-cost evidence pending",
            "Original >=20% quality-constrained routing-token target remains unmet; compact-profile absolute reductions are not that comparison",
            "Actual browser, old Windows/edge and buyer acceptance pending",
        ],
        "note": "Run make catalogbridge-test for engineering checks; this command never substitutes fixtures for acceptance.",
    }
    print(json.dumps(report, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
