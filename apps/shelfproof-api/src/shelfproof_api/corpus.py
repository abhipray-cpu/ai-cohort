"""Bounded official-USDA acquisition and explicit, conservative package-fact mapping."""

import codecs
import hashlib
import json
import re
import shutil
import stat
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from contracts.shelfproof import FactPack

from .core import canonical, digest

USDA_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2026-04-30.zip"
RELEASE = "2026-04-30"
DICTIONARY_URL = "https://fdc.nal.usda.gov/docs/Download_Field_Descriptions_Oct2020.pdf"


def source_group(food):
    """Conservative source-owner grouping, not a claim of expert-verified family identity."""
    owner = food.get("brandOwner") or food.get("brandName")
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("source grouping needs an owner or explicit brand")
    value = re.sub(r"['’]s\b", "", owner.casefold())
    value = " ".join(re.findall(r"\w+", value))
    value = re.sub(r"\s+(?:incorporated|inc|llc|ltd|corporation|corp)$", "", value)
    return digest({"published_owner": value, "scheme": "source-owner-v2"})


def regroup_inventory(source, output):
    source, output = Path(source), Path(output)
    manifest = json.loads((source / "manifest.json").read_text())
    raw = (source / "records.jsonl").read_bytes()
    if digest(raw) != manifest["records_hash"]:
        raise ValueError("source manifest hash mismatch")
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    for row in rows:
        if digest(row["raw"]) != row["raw_hash"]:
            raise ValueError("raw source hash mismatch")
        row["group"] = source_group(row["raw"])
        bucket = int(row["group"][:8], 16) % 10
        row["split"] = "development" if bucket < 6 else "calibration" if bucket < 8 else "locked"
    output.mkdir(parents=True, exist_ok=False)
    data = "".join(canonical(row) + "\n" for row in rows).encode()
    (output / "records.jsonl").write_bytes(data)
    result = {
        **manifest,
        "schema": "shelfproof-usda-inventory-v2",
        "records_hash": digest(data),
        "parent_manifest_hash": digest(manifest),
        "source_artifact_directory": str(source.resolve()),
        "grouping": "normalized-published-owner-v2-conservative-not-expert-family",
        "heuristic_source_owner_groups": len({r["group"] for r in rows}),
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "regrouped_utc": datetime.now(UTC).isoformat(),
    }
    result.pop("heuristic_brand_category_groups", None)
    (output / "manifest.json").write_text(canonical(result))
    return result


def iter_foods(stream, chunk_size=65536, max_record_bytes=2 * 1024 * 1024):
    """Incremental UTF-8/JSON decoding; never loads the multi-GB member into memory."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    parser = json.JSONDecoder()
    buffer = ""
    eof = False
    found = False
    after_item = False
    after_comma = False
    while True:
        if not found:
            match = re.search(r'"BrandedFoods"\s*:\s*\[', buffer)
            if match:
                buffer = buffer[match.end() :]
                found = True
            elif len(buffer) > 4096 or eof:
                raise ValueError("missing BrandedFoods array")
        if found:
            buffer = buffer.lstrip()
            if buffer and after_item:
                if buffer.startswith("]"):
                    return
                if not buffer.startswith(","):
                    raise ValueError("missing JSON array separator")
                buffer = buffer[1:].lstrip()
                after_item, after_comma = False, True
            if buffer.startswith("]"):
                if after_comma:
                    raise ValueError("trailing JSON comma")
                return
            if buffer:
                try:
                    item, end = parser.raw_decode(buffer)
                except json.JSONDecodeError:
                    if eof:
                        raise ValueError("malformed or incomplete USDA JSON") from None
                else:
                    if not isinstance(item, dict) or len(buffer[:end].encode()) > max_record_bytes:
                        raise ValueError("invalid or oversized USDA record")
                    yield item
                    buffer = buffer[end:]
                    after_item, after_comma = True, False
                    continue
            if len(buffer.encode()) > max_record_bytes:
                raise ValueError("USDA record exceeds bound")
            if eof:
                raise ValueError("incomplete USDA array")
        raw = stream.read(chunk_size)
        eof = not raw
        buffer += decoder.decode(raw, final=eof)


def normalize_food(food, release):
    if food.get("marketCountry") != "United States":
        raise ValueError("country")
    if food.get("discontinuedDate"):
        raise ValueError("discontinued")
    if re.search(
        r"supplement|infant|tobacco|pet food|animal feed",
        str(food.get("brandedFoodCategory", "")),
        re.IGNORECASE,
    ):
        raise ValueError("out_of_scope_category")
    if not isinstance(food.get("brandName"), str) or not food["brandName"].strip():
        raise ValueError("missing_brand_name_no_owner_substitution")
    package = food.get("packageWeight")
    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*(fl oz|kg|ml|oz|lb|g|l)\s*", str(package or ""), re.IGNORECASE
    )
    if not match:
        raise ValueError("missing_or_ambiguous_net_package_quantity")
    gtin = food.get("gtinUpc")
    if not isinstance(gtin, str) or not re.fullmatch(r"\d{8,14}", gtin):
        raise ValueError("invalid_literal_gtin")
    if type(food.get("fdcId")) is not int:
        raise ValueError("invalid_fdc_id")
    facts = FactPack(
        product_id=gtin,
        brand=food["brandName"],
        name=food.get("description"),
        net_quantity=match[1],
        net_unit=match[2].lower(),
        ingredients=food.get("ingredients"),
        source_ref=f"USDA:FDC:{food['fdcId']}@{release}",
    )
    if len(f"{facts.brand} {facts.name} {match[1]} {facts.net_unit}") > 150:
        raise ValueError("identity_does_not_fit_title")
    return facts


def validate_archive(archive):
    entries = archive.infolist()
    if not 1 <= len(entries) <= 100 or sum(e.file_size for e in entries) > 4 * 1024**3:
        raise ValueError("archive expansion/count exceeds bound")
    seen = set()
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if (
            entry.filename in seen
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in entry.filename
            or ":" in entry.filename
            or stat.S_ISLNK(entry.external_attr >> 16)
            or entry.file_size > max(entry.compress_size * 100, 1024 * 1024)
        ):
            raise ValueError("unsafe/ambiguous archive entry")
        seen.add(entry.filename)
    data = [e for e in entries if e.filename.lower().endswith(".json")]
    if len(data) != 1:
        raise ValueError("exactly one JSON member required")
    return data[0]


def acquire(
    destination,
    *,
    target=1000,
    max_scanned=250000,
    url=USDA_URL,
    reviewed_dictionary_hash=None,
    expected_archive_sha256=None,
):
    """New-only, bounded download. No provider calls. Report prefix denominators honestly."""
    if url != USDA_URL or not 1 <= target <= 1000 or not 1 <= max_scanned <= 1000000:
        raise ValueError("only frozen official source and bounded inventory supported")
    root = Path(destination)
    archive_path = root / "usda-branded-2026-04-30.zip"
    acquired_utc = datetime.now(UTC).isoformat()
    pending = None
    if reviewed_dictionary_hash is None and expected_archive_sha256 is None:
        root.mkdir(parents=True, exist_ok=False)
        if shutil.disk_usage(root).free < 2 * 1024**3:
            raise ValueError("at least 2 GiB free required")
        sha = hashlib.sha256()
        received = 0
        started = time.monotonic()
        with urllib.request.urlopen(url, timeout=30) as response, archive_path.open("xb") as output:
            if urllib.parse.urlparse(response.url).hostname != "fdc.nal.usda.gov":
                raise ValueError("unexpected source redirect")
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > 260 * 1024 * 1024 or time.monotonic() - started > 600:
                    raise ValueError("download exceeds byte/time allowance")
                sha.update(chunk)
                output.write(chunk)
        archive_hash = sha.hexdigest()
    else:
        if (root / "acquisition.json").exists():
            pending = json.loads((root / "acquisition.json").read_text())
        elif expected_archive_sha256 and re.fullmatch(r"[0-9a-f]{64}", expected_archive_sha256):
            pending = {
                "archive_sha256": expected_archive_sha256,
                "archive_bytes": archive_path.stat().st_size,
                "retrieved_utc": datetime.fromtimestamp(
                    archive_path.stat().st_mtime, UTC
                ).isoformat(),
            }
        else:
            raise ValueError("verified existing-download hash required")
        with archive_path.open("rb") as file:
            archive_hash = hashlib.file_digest(file, "sha256").hexdigest()
        if archive_hash != pending["archive_sha256"]:
            raise ValueError("frozen archive hash changed")
        received = pending["archive_bytes"]
        acquired_utc = pending["retrieved_utc"]
        if (root / "records.jsonl").exists() or (root / "manifest.json").exists():
            raise FileExistsError(
                "curation artifacts already exist; never overwrite evaluated corpus"
            )
    excluded = Counter()
    selected = []
    seen_gtin = set()
    seen_exact = set()
    scanned = 0
    dictionaries = []
    with zipfile.ZipFile(archive_path) as archive:
        entry = validate_archive(archive)
        for item in archive.infolist():
            if (
                item.filename.lower().endswith((".pdf", ".xlsx", ".txt"))
                and item.file_size < 5 * 1024 * 1024
            ):
                raw = archive.read(item)
                filename = Path(item.filename).name
                if (root / filename).exists():
                    if (root / filename).read_bytes() != raw:
                        raise ValueError("dictionary hash collision or changed local dictionary")
                else:
                    (root / filename).write_bytes(raw)
                dictionaries.append({"file": filename, "sha256": digest(raw)})
        if not dictionaries:
            # The actual 2026 JSON release contains only its data member, despite
            # the download page saying every archive includes a dictionary.
            dictionary = root / "Download_Field_Descriptions_Oct2020.pdf"
            if dictionary.exists():
                raw = dictionary.read_bytes()
                previous = (pending or {}).get("dictionary_files", [])
                if not any(
                    d.get("sha256") == digest(raw) and d.get("url") == DICTIONARY_URL
                    for d in previous
                ):
                    raise ValueError("unverified cached external dictionary")
            else:
                with urllib.request.urlopen(DICTIONARY_URL, timeout=30) as response:
                    if urllib.parse.urlparse(response.url).hostname != "fdc.nal.usda.gov":
                        raise ValueError("unexpected dictionary redirect")
                    raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024 or not raw.startswith(b"%PDF-"):
                    raise ValueError("official dictionary response is not a bounded PDF")
                with dictionary.open("xb") as file:
                    file.write(raw)
            dictionaries.append(
                {
                    "file": dictionary.name,
                    "sha256": digest(raw),
                    "url": DICTIONARY_URL,
                    "origin": "external_official_fallback_not_bundled",
                }
            )
        if reviewed_dictionary_hash is None:
            pending = {
                "schema": "shelfproof-usda-acquisition-v1",
                "url": url,
                "release": RELEASE,
                "retrieved_utc": acquired_utc,
                "archive_bytes": received,
                "archive_sha256": archive_hash,
                "dictionary_files": dictionaries,
                "mapping_pending": True,
            }
            (root / "acquisition.json").write_text(canonical(pending), encoding="utf-8")
            return pending
        if reviewed_dictionary_hash not in {d["sha256"] for d in dictionaries}:
            raise ValueError("exact reviewed official dictionary hash required")
        with archive.open(entry) as stream:
            for food in iter_foods(stream):
                scanned += 1
                try:
                    if len(canonical(food).encode()) > 65536:
                        raise ValueError("raw_record_exceeds_64KiB")
                    facts = normalize_food(food, RELEASE)
                except ValueError as exc:
                    label = str(exc).split("\n", 1)[0]
                    excluded[label if len(label) < 100 else "invalid_fact_contract"] += 1
                else:
                    semantic = digest(
                        {
                            k: v
                            for k, v in facts.model_dump(mode="json").items()
                            if k not in {"product_id", "source_ref"}
                        }
                    )
                    if facts.product_id in seen_gtin or semantic in seen_exact:
                        excluded["duplicate_gtin_or_exact_content"] += 1
                    else:
                        seen_gtin.add(facts.product_id)
                        seen_exact.add(semantic)
                        # Conservative brand/category grouping keeps related variants together
                        # within this sampled prefix; it is not expert-verified family identity.
                        group = digest(
                            {
                                "brand": facts.brand.casefold(),
                                "category": food.get("brandedFoodCategory", "").casefold(),
                            }
                        )
                        split = (
                            "development"
                            if int(group[:8], 16) % 10 < 6
                            else "calibration"
                            if int(group[:8], 16) % 10 < 8
                            else "locked"
                        )
                        selected.append(
                            {
                                "facts": facts.model_dump(mode="json"),
                                "raw": food,
                                "raw_hash": digest(food),
                                "group": group,
                                "split": split,
                            }
                        )
                if len(selected) >= target or scanned >= max_scanned:
                    break
    with (root / "records.jsonl").open("x", encoding="utf-8") as file:
        file.write("".join(canonical(row) + "\n" for row in selected))
    manifest = {
        "schema": "shelfproof-usda-inventory-v1",
        "url": url,
        "release": RELEASE,
        "retrieved_utc": acquired_utc,
        "curated_utc": datetime.now(UTC).isoformat(),
        "archive_bytes": received,
        "archive_sha256": archive_hash,
        "reviewed_dictionary_hash": reviewed_dictionary_hash,
        "dictionary_files": dictionaries,
        "scanned_prefix": scanned,
        "eligible_selected": len(selected),
        "independent_gtins": len(seen_gtin),
        "heuristic_brand_category_groups": len({r["group"] for r in selected}),
        "split_counts": dict(Counter(r["split"] for r in selected)),
        "exclusions": dict(excluded),
        "records_hash": digest((root / "records.jsonl").read_bytes()),
        "mapping": "literal-brandName-description-ingredients-single-packageWeight-v1",
        "serving_size_used_as_package": False,
        "whole_release_scanned": False,
        "human_labels": 0,
        "source_scope": "USDA source-snapshot fidelity; not current-package truth",
        "license": "USDA FoodData Central CC0 https://fdc.nal.usda.gov/api-guide/",
    }
    (root / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return manifest
