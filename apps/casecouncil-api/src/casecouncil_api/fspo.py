"""Bounded attributed FSPO acquisition for private evaluation, not product promotion.

Source permission: https://fspo.ie/governance/reuse.asp (checked 19 October 2026).
Originals and final outcomes remain evaluator-only. No FOS source is fetched here.
"""

import hashlib
import html
import json
import math
import re
import shutil
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .evidence import extract, sha

BASE = "https://www.fspo.ie/complaint-outcomes/investigation-services/legally-binding-decisions/"
REUSE = "https://fspo.ie/governance/reuse.asp"
ATTRIBUTION = "Source: Financial Services and Pensions Ombudsman, Ireland (FSPO). Copyright FSPO. Reused under https://fspo.ie/governance/reuse.asp. No endorsement."


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_listing(value):
    rows = []
    for block in re.split(r'<div class="decision col-12">', value)[1:]:
        match = re.search(r'href="([^"]+/documents/(\d{4}-\d{4})\.pdf)"', block)
        if not match:
            raise ValueError("unrecognized official decision entry")
        url, reference = match.groups()
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {"fspo.ie", "www.fspo.ie"}:
            raise ValueError("non-FSPO document link")

        def field(name, block=block):
            found = re.search(r"<span>" + re.escape(name) + r":</span>(.*?)</p", block, re.DOTALL)
            if not found:
                raise ValueError("missing listing metadata: " + name)
            return plain(found[1])

        if field("Sector") != "Insurance" or field("Product/Service") != "Motor":
            raise ValueError("source filter mismatch")
        rows.append(
            {
                "reference": reference,
                "url": url,
                "outcome": field("Outcome"),
                "conduct": field("Primary Conduct Complained Of"),
                "year": field("Year"),
            }
        )
    return rows


def party_packet(text, reference):
    heading = re.search(
        r"(?im)^\s*LEGALLY\s+BINDING\s+DECISION\s+OF\s+THE\s+FINANCIAL\s+SERVICES\s+AND\s+PENSIONS\s+OMBUDSMAN[^\n]*\n",
        text,
    )
    if not heading:
        raise ValueError("missing body heading")
    decision = re.search(r"(?im)^\s*Decision\s*$", text[heading.end() :])
    if not decision:
        raise ValueError("no unambiguous decision boundary")
    start, end = heading.end(), heading.end() + decision.start()
    body = text[start:end].strip()
    if len(body) < 200 or len(body) > 200000:
        raise ValueError("party-summary length unsupported")
    if not re.search(r"(?i)complainant(?:[’']s|s[’'])\s+case", body) or not re.search(
        r"(?i)provider(?:[’']s|s[’'])\s+case", body
    ):
        raise ValueError("both attributed party sections required")
    if reference in body or re.search(
        r"(?i)preliminary decision|ombudsman (?:upheld|rejected|found)|(?:my|final) decision|outcome\s*:",
        body,
    ):
        raise ValueError("potential outcome leakage in party section; exclude pending review")
    return {
        "text": body,
        "start": start,
        "end": end,
        "scope": "exact pre-decision party-summary excerpt, not original case files or adjudicator findings",
    }


def fetch(url, maximum=10 * 1024 * 1024):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"fspo.ie", "www.fspo.ie"}:
        raise ValueError("restricted acquisition host")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CaseCouncil-SourceAudit/1.0 (bounded attributed research; no advertising)"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if urllib.parse.urlsplit(response.url).hostname not in {"fspo.ie", "www.fspo.ie"}:
            raise ValueError("unexpected source redirect")
        raw = response.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("source exceeds intake limit")
    return raw


def acquire(output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    for folder in ("raw", "inputs", "gold", "metadata"):
        (root / folder).mkdir()
    (root / "ATTRIBUTION.txt").write_text(
        ATTRIBUTION + "\nPrivate validation only; not advertising or endorsement.\n"
    )
    (root / "metadata/reuse.html").write_bytes(fetch(REUSE))
    listing = []
    for page in range(1, 10):
        url = (
            BASE + "display.asp?sector=2&product=11&conduct=0&outcome=0&dyear=0&mypage=" + str(page)
        )
        raw = fetch(url)
        (root / f"metadata/listing-{page}.html").write_bytes(raw)
        decoded = raw.decode("utf-8-sig")
        count = re.search(r"There are (\d+) decisions matching", decoded)
        if not count or int(count[1]) > 225:
            raise ValueError("unexpected inventory size; review before extending acquisition")
        listing.extend(parse_listing(decoded))
        if page >= math.ceil(int(count[1]) / 25):
            break
        time.sleep(0.15)
    if len({r["reference"] for r in listing}) != len(listing) or len(listing) != int(count[1]):
        raise ValueError("incomplete or duplicate inventory")
    (root / "metadata/inventory.json").write_text(json.dumps(listing, indent=2))

    def document(row):
        try:
            raw = fetch(row["url"])
            (root / ("raw/" + row["reference"] + ".pdf")).write_bytes(raw)
            source = extract("source", row["reference"] + ".pdf", raw)
            (root / ("raw/" + row["reference"] + ".txt")).write_text(source["text"])
            return {
                **row,
                "sha256": sha(raw),
                "pages": source["pages"],
                "text": source["text"],
                "extraction_partial": source["partial"],
            }
        except (ValueError, OSError) as exc:
            return {**row, "error": type(exc).__name__}

    with ThreadPoolExecutor(max_workers=2) as pool:
        documents = list(pool.map(document, listing))
    return build_manifest(root, documents, listing)


def reprepare(source, output):
    """Offline new-version preparation; never overwrite or reacquire originals."""
    source, root = Path(source), Path(output)
    root.mkdir(parents=True, exist_ok=False)
    for folder in ("raw", "metadata"):
        shutil.copytree(source / folder, root / folder)
    for folder in ("inputs", "gold"):
        (root / folder).mkdir()
    shutil.copyfile(source / "ATTRIBUTION.txt", root / "ATTRIBUTION.txt")
    listing = json.loads((root / "metadata/inventory.json").read_text())
    documents = []
    for row in listing:
        raw = (root / ("raw/" + row["reference"] + ".pdf")).read_bytes()
        extracted = extract("source", row["reference"] + ".pdf", raw)
        documents.append(
            {
                **row,
                "sha256": sha(raw),
                "pages": extracted["pages"],
                "text": extracted["text"],
                "extraction_partial": extracted["partial"],
            }
        )
    return build_manifest(root, documents, listing)


def build_manifest(root, documents, listing):
    eligible, excluded = [], []
    mapping = {
        "Rejected": "do_not_uphold",
        "Upheld": "uphold",
        "Substantially upheld": "partial_uphold",
        "Partially upheld": "partial_uphold",
    }
    for row in documents:
        try:
            if "error" in row or row["extraction_partial"]:
                raise ValueError("document unavailable or partial extraction")
            packet = party_packet(row["text"], row["reference"])
            cid = "motor_" + hashlib.sha256(row["reference"].encode()).hexdigest()[:16]
            data = (
                ATTRIBUTION
                + "\nJurisdiction: Ireland. Retrospective party-summary replay only.\n"
                + packet["text"]
            ).encode()
            (root / f"inputs/{cid}.txt").write_bytes(data)
            (root / f"gold/{cid}.json").write_text(
                json.dumps(
                    {
                        "issues": {"complaint": mapping[row["outcome"]]},
                        "source_reference": row["reference"],
                        "source_outcome": row["outcome"],
                        "label_scope": "whole published complaint, not independent issue-level gold",
                    },
                    indent=2,
                )
            )
            eligible.append(
                {
                    "id": cid,
                    "group": cid,
                    "split": "development"
                    if int(cid[-2:], 16) % 10 < 6
                    else "calibration"
                    if int(cid[-2:], 16) % 10 < 8
                    else "test",
                    "cohort": "retrospective_decision",
                    "context": {
                        "title": "Irish motor-insurance party-summary replay",
                        "jurisdiction": "IE",
                        "product": "motor_insurance",
                        "issues": [{"id": "complaint", "title": row["conduct"]}],
                        "facts": "Source is an Irish FSPO party-summary excerpt, not verified raw case evidence. Review only supplied statements and quotes; do not apply UK law or infer the later outcome.",
                        "draft": "",
                        "missing": [
                            "Full original policy and case-file evidence are unavailable; retrospective party summaries only."
                        ],
                    },
                    "documents": [
                        {"path": f"inputs/{cid}.txt", "kind": "complaint", "sha256": sha(data)}
                    ],
                    "gold_path": f"gold/{cid}.json",
                    "provenance": {
                        k: row[k] for k in ("reference", "url", "sha256", "pages", "year")
                    },
                    "excerpt": {k: v for k, v in packet.items() if k != "text"},
                }
            )
        except (ValueError, KeyError) as exc:
            excluded.append({"reference": row["reference"], "reason": str(exc)})
    manifest = {
        "schema_version": 1,
        "source": "FSPO Ireland motor decisions",
        "attribution": ATTRIBUTION,
        "permission": {
            "basis": "licensed",
            "reference": "Published FSPO reuse permission: "
            + REUSE
            + "; private attributed validation, not advertising; checked 2026-10-19",
            "expires": time.time() + 30 * 86400,
            "egress": False,
        },
        "cases": eligible,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    report = {
        "source": BASE,
        "permission": REUSE,
        "listed": len(listing),
        "downloaded": sum("text" in r for r in documents),
        "eligible": len(eligible),
        "excluded": excluded,
        "pages": sum(r.get("pages", 0) for r in documents),
        "real_data_inference_run": False,
        "uk_validation": False,
        "full_product_accepted": False,
    }
    (root / "acquisition-report.json").write_text(json.dumps(report, indent=2))
    return report
