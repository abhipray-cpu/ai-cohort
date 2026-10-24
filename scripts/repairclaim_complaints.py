"""Bounded official public-report metadata acquisition; not private invoices or verified repair facts."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from repairclaim_api.sources import SourceFetcher

COHORTS = [("CR-V", 2017), ("HR-V", 2016), ("Pilot", 2016), ("Odyssey", 2018)]


def minimize(raw, cohort):
    identifier = str(raw.get("odiNumber", ""))
    if not re.fullmatch(r"[0-9]{1,15}", identifier):
        return None
    model, year = cohort
    products = raw.get("products", [])
    if not isinstance(products, list):
        return None
    matching = [
        p
        for p in products
        if isinstance(p, dict)
        and str(p.get("productMake", p.get("make", ""))).casefold() == "honda"
        and str(p.get("productModel", p.get("model", ""))).casefold() == model.casefold()
        and str(p.get("productYear", p.get("modelYear", ""))) == str(year)
    ]
    if not matching:
        return None
    return {
        "record_type": "public_unverified_consumer_complaint_metadata",
        "odi_number": identifier,
        "source_record_sha256": hashlib.sha256(
            json.dumps(raw, sort_keys=True).encode()
        ).hexdigest(),
        "facts": {"model": model, "model_year": year},
        "excluded_fields": [
            "vin",
            "summary",
            "location",
            "incident_date",
            "complaint_date",
            "contact",
        ],
        "not_established": [
            "component",
            "repair_date",
            "in_service_date",
            "repair_mileage",
            "payment",
            "diagnosis",
            "invoice",
        ],
    }


def acquire(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    fetcher = SourceFetcher(max_bytes=20 * 1024 * 1024)
    records, manifest, seen = [], [], set()
    for model, year in COHORTS:
        url = "https://api.nhtsa.gov/complaints/complaintsByVehicle?" + urlencode(
            {"make": "Honda", "model": model, "modelYear": year}
        )
        response = fetcher.fetch(url)
        data = json.loads(response["body"])
        rows = data["results"]
        candidates = []
        for raw in rows:
            record = minimize(raw, (model, year))
            if record and record["odi_number"] not in seen:
                seen.add(record["odi_number"])
                record["source_url"] = response["url"]
                candidates.append(record)
        # Selection is frozen by identity hash, never by product/model outcome.
        candidates.sort(key=lambda r: hashlib.sha256(r["odi_number"].encode()).hexdigest())
        chosen = candidates[:100]
        records.extend(chosen)
        entry = {
            "model": model,
            "year": year,
            "url": response["url"],
            "response_sha256": response["sha256"],
            "bytes": len(response["body"]),
            "received_count": len(rows),
            "valid_unique_metadata": len(candidates),
            "selected": len(chosen),
            "record_keys": sorted(rows[0]) if rows else [],
            "product_keys": sorted(rows[0].get("products", [{}])[0])
            if rows and rows[0].get("products")
            else [],
            "acquired_at": datetime.now(UTC).isoformat(),
        }
        manifest.append(entry)
        # Raw payload is deliberately not persisted: it contains VINs and narratives.
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (out / "records.json").write_text(json.dumps(records, indent=2))
        print(
            json.dumps(
                {
                    k: entry[k]
                    for k in (
                        "model",
                        "year",
                        "received_count",
                        "valid_unique_metadata",
                        "selected",
                    )
                }
            ),
            flush=True,
        )
    return records


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = acquire(args.out)
    print(
        json.dumps(
            {
                "selected_records": len(records),
                "actual_private_invoices": 0,
                "independent_labels": False,
            }
        )
    )
    raise SystemExit(0 if len(records) == 400 else 1)
