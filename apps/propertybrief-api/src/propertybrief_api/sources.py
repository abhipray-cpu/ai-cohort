"""Registry-controlled NYC source access with bounded paging and identity scope."""

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Definition:
    dataset: str
    title: str
    key: str
    identity_field: str
    required: bool = True

    @property
    def url(self):
        return f"https://data.cityofnewyork.us/resource/{self.dataset}.json"

    @property
    def catalog(self):
        return f"https://data.cityofnewyork.us/d/{self.dataset}"


DEFINITIONS = {
    "buildings": Definition("kj4p-ruqc", "HPD buildings", "buildingid", "buildingid", False),
    "registrations": Definition(
        "tesw-yqqr", "Dwelling registrations", "registrationid", "buildingid", False
    ),
    "hpd_violations": Definition("wvxf-dwi5", "Housing violations", "violationid", "buildingid"),
    "hpd_complaints": Definition(
        "ygpa-z7cr", "Housing complaints and problems", "problem_id", "building_id"
    ),
    "vacate": Definition(
        "tb8q-a3ar", "Repair / vacate orders", "vacate_order_number", "building_id"
    ),
    "underlying": Definition("xpbf-ithr", "Underlying conditions", "building_id", "building_id"),
    "aep": Definition("hcir-3275", "Alternative enforcement", "building_id", "building_id"),
    "dob_complaints": Definition("eabe-havv", "DOB complaints", "complaint_number", "bin"),
    "dob_violations": Definition("3h2n-5cm9", "DOB violations", "isn_dob_bis_viol", "bin"),
    "dob_ecb": Definition("6bgk-3dad", "DOB ECB violations", "isn_dob_bis_extract", "bin"),
}
REQUIRED = tuple(key for key, item in DEFINITIONS.items() if item.required)
BOROUGHS = {"Manhattan": "1", "Bronx": "2", "Brooklyn": "3", "Queens": "4", "Staten Island": "5"}


def derive_bbl(boro, block, lot):
    if not all(re.fullmatch(r"\d+", str(v)) for v in (boro, block, lot)):
        raise ValueError("Invalid parcel identifiers")
    b, k, l = map(int, (boro, block, lot))
    if b not in range(1, 6) or not 0 < k < 100000 or not 0 < l < 10000:
        raise ValueError("Invalid parcel identifiers")
    return f"{b}{k:05}{l:04}"


def candidate(row):
    if row.get("recordstatus", "Active").lower() != "active":
        raise ValueError("Inactive building")
    bbl = derive_bbl(row.get("boroid"), row.get("block"), row.get("lot"))
    bid = str(row.get("buildingid", ""))
    if not bid.isdigit() or int(bid) == 0:
        raise ValueError("Invalid building ID")
    bin_value = row.get("bin")
    if bin_value and (not re.fullmatch(r"[1-5]\d{6}", bin_value) or bin_value[0] != bbl[0]):
        raise ValueError("Invalid or conflicting building identifier")
    return {
        "id": bid,
        "building_id": bid,
        "bin": bin_value,
        "bbl": bbl,
        "address": f"{row.get('housenumber', '')} {row.get('streetname', '')}".strip(),
        "borough": row.get("boro", ""),
        "source": "buildings",
        "raw": row,
        "retrieved_at": now(),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Source redirects are not permitted")


class SourceClient:
    def __init__(self, *, get=None, page_size=1000, max_pages=10, metadata=True, reserve=None):
        self.get = get or self._get
        self.page_size, self.max_pages, self.metadata = page_size, max_pages, metadata
        self.reserve = reserve
        self.deadline = time.monotonic() + 900
        self.attempts = 0
        self.bytes = 0

    def _get(self, url, params):
        if urllib.parse.urlsplit(url).hostname != "data.cityofnewyork.us":
            raise ValueError("Unapproved source host")
        headers = {"User-Agent": "PropertyBrief/0.1 (public-record investigation)"}
        if os.getenv("NYC_OPEN_DATA_APP_TOKEN"):
            headers["X-App-Token"] = os.environ["NYC_OPEN_DATA_APP_TOKEN"]
        request = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params), headers=headers
        )
        for attempt in range(2):
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Source deadline exceeded")
            if self.reserve:
                self.reserve()
            self.attempts += 1
            if self.attempts > 48:
                raise ValueError("HTTP budget exhausted")
            try:
                with urllib.request.build_opener(NoRedirect).open(
                    request, timeout=min(15, remaining)
                ) as response:
                    data = response.read(2 * 1024 * 1024 + 1)
                self.bytes += len(data)
                if len(data) > 2 * 1024 * 1024 or self.bytes > 20 * 1024 * 1024:
                    raise ValueError("Source byte budget exceeded")
                return json.loads(data)
            except urllib.error.HTTPError as error:
                if attempt or error.code not in (429, 502, 503, 504):
                    raise
                delay = min(2, max(0, int(error.headers.get("Retry-After", "1"))))
                if time.monotonic() + delay >= self.deadline:
                    raise TimeoutError("Source deadline exceeded") from error
                time.sleep(delay)

    def resolve(self, value):
        params = {
            "$limit": 21,
            "$order": "buildingid",
            "boroid": BOROUGHS[value.borough],
            "recordstatus": "Active",
        }
        if value.bin:
            params["bin"] = value.bin
        elif value.bbl:
            if value.bbl[0] != BOROUGHS[value.borough]:
                raise ValueError("BBL conflicts with borough")
            params.update(block=str(int(value.bbl[1:6])), lot=str(int(value.bbl[6:])))
        else:
            address = re.fullmatch(
                r"([\dA-Za-z-]+(?:\s+(?:FRONT|REAR))?)\s+(.+)", value.address.upper()
            )
            if not address:
                raise ValueError(
                    "Use house number and full official street name, or supply BIN/BBL"
                )
            params.update(housenumber=address[1], streetname=address[2])
        rows = self.get(DEFINITIONS["buildings"].url, params)
        if not isinstance(rows, list) or len(rows) > 20:
            raise ValueError("Too many or malformed candidates; supply a precise BIN")
        result = []
        for row in rows:
            try:
                item = candidate(row)
                if value.bin and item["bin"] != value.bin or value.bbl and item["bbl"] != value.bbl:
                    continue
                if item["bbl"][0] != BOROUGHS[value.borough]:
                    continue
                result.append(item)
            except ValueError:
                continue
        return result

    def fetch(self, source, identity):
        from propertybrief_api.evidence import normalize_record

        definition = DEFINITIONS.get(source)
        if not definition or not definition.required:
            raise ValueError("Unknown investigation tool")
        started = now()
        raw, records, flags, seen = [], [], [], set()
        completeness, outcome, error = "unknown", "unavailable", None
        before = after = None
        params = {"$limit": self.page_size, "$order": definition.key}
        if definition.identity_field == "bin":
            if source == "dob_violations":
                bbl = identity["bbl"]
                if not re.fullmatch(r"[1-5]\d{9}", bbl):
                    raise ValueError("Invalid parcel scope")
                parcel = (
                    f"boro = '{bbl[0]}' AND block = '{bbl[1:6]}' AND lot = '{int(bbl[6:]):05d}'"
                )
                bin_value = identity.get("bin")
                if bin_value:
                    if not re.fullmatch(r"[1-5]\d{6}", bin_value):
                        raise ValueError("Invalid building scope")
                    params["$where"] = (
                        f"bin = '{bin_value}' OR ((bin IS NULL OR bin = '') AND {parcel})"
                    )
                else:
                    params["$where"] = parcel
            elif identity.get("bin"):
                params["bin"] = identity["bin"]
            else:
                return self._result(
                    source,
                    identity,
                    started,
                    [],
                    [],
                    "unknown",
                    "unavailable",
                    ["missing_bin"],
                    None,
                    None,
                    params,
                )
        else:
            params[definition.identity_field] = identity["building_id"]
        try:
            if self.metadata:
                before = self.get(
                    f"https://data.cityofnewyork.us/api/views/{definition.dataset}.json", {}
                )
            for page in range(self.max_pages):
                rows = self.get(definition.url, {**params, "$offset": page * self.page_size})
                if not isinstance(rows, list) or len(rows) > self.page_size:
                    raise ValueError("Invalid source page")
                for item in rows:
                    if not isinstance(item, dict) or definition.key not in item:
                        raise ValueError("Source schema drift: missing row key")
                    row_key = str(item[definition.key])
                    if row_key in seen:
                        flags.append("duplicate_key")
                        continue
                    seen.add(row_key)
                    raw.append(item)
                    try:
                        record = normalize_record(source, item, identity)
                        records.append(record)
                        if "identity_conflict" in record["flags"]:
                            flags.append("identity_conflict")
                    except ValueError:
                        flags.append("identity_conflict")
                if len(rows) < self.page_size:
                    completeness = "complete_for_query"
                    break
            else:
                completeness = "truncated"
            if self.metadata:
                after = self.get(
                    f"https://data.cityofnewyork.us/api/views/{definition.dataset}.json", {}
                )
                if before.get("rowsUpdatedAt") != after.get("rowsUpdatedAt"):
                    flags.append("source_changed_during_acquisition")
                    completeness = "drift_detected"
            if flags:
                completeness = "unknown" if "identity_conflict" in flags else completeness
            outcome = (
                "partial"
                if completeness != "complete_for_query"
                else "success"
                if records
                else "no_records"
            )
        except (OSError, ValueError, TimeoutError, TypeError, KeyError) as exception:
            error = type(exception).__name__
            completeness = "unknown"
            outcome = "partial" if records else "unavailable"
        return self._result(
            source,
            identity,
            started,
            raw,
            records,
            completeness,
            outcome,
            flags,
            error,
            {"before": before, "after": after},
            params,
        )

    def _result(
        self,
        source,
        identity,
        started,
        raw,
        records,
        completeness,
        outcome,
        flags,
        error,
        metadata,
        params,
    ):
        return {
            "source": source,
            "dataset": DEFINITIONS[source].dataset,
            "catalog": DEFINITIONS[source].catalog,
            "identity": identity["building_id"],
            "query": params,
            "started_at": started,
            "retrieved_at": now(),
            "raw": raw,
            "records": records,
            "sha256": digest(raw),
            "metadata": metadata,
            "completeness": completeness,
            "outcome": outcome,
            "flags": sorted(set(flags)),
            "error": error,
            "count": len(records),
        }
