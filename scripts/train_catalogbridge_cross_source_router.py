"""Second candidate: WDC development fit/tune, separate legacy-source qualification."""

import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
from catalogbridge_api.local_router import PairRouter, feature_vector, feature_version
from catalogbridge_api.matching import conflicts, digest
from contracts.catalogbridge import Product

from scripts.audit_catalogbridge_corpus import load_rows, normalize_legacy_pair
from scripts.train_catalogbridge_local_router import (
    fit_trees,
    group_role,
    independent_band,
    order,
    predict,
)


def thresholds(rows, scores):
    result = {}
    coverage = 0
    for label, grid in (
        (0, (0.001, 0.005, 0.01, 0.02, 0.05, 0.1)),
        (1, (0.9, 0.95, 0.98, 0.99, 0.995, 0.999)),
    ):
        choices = []
        for threshold in grid:
            selected = [
                i
                for i, r in enumerate(rows)
                if (scores[i] >= threshold if label else scores[i] <= threshold)
                and (not label or not r["conflicts"])
            ]
            correct = sum(rows[i]["label"] == label for i in selected)
            if len(selected) >= 100 and correct / len(selected) >= 0.995:
                choices.append((len(selected), threshold))
        choice = max(choices) if choices else (0, None)
        result[str(label)] = choice[1]
        coverage += choice[0]
    return result, coverage


def train(corpus, output):
    if output.exists():
        raise ValueError("preserve earlier evidence")
    sources = {}
    rows = {}
    invalid = 0
    identities = set()
    texts = set()
    for hard in (20, 50, 80):
        path = corpus / f"{hard}pair.zip"
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if "train_large" not in member and "valid_large" not in member:
                    continue
                for raw in load_rows(archive, member):
                    a, b = str(raw["cluster_id_left"]), str(raw["cluster_id_right"])
                    left_tune = group_role(a, a) == "tune"
                    right_tune = group_role(b, b) == "tune"
                    if left_tune != right_tune:
                        continue
                    role = "tune" if left_tune else "fit"
                    if role == "fit" and "valid_large" in member:
                        continue
                    try:
                        # Published integer labels, not the legacy string adapter.
                        from catalogbridge_api.corpus import normalize_pair

                        pair = normalize_pair(raw)
                    except ValueError:
                        invalid += 1
                        continue
                    left, right = (
                        Product(**pair["input"]["supplier"]),
                        Product(**pair["input"]["master"]),
                    )
                    for p in (left, right):
                        identities.add(p.id)
                        texts.add(digest([p.title.casefold(), p.brand.casefold()]))
                    key = "#".join(sorted((left.id, right.id)))
                    value = {
                        "id": key,
                        "offers": [left.id, right.id],
                        "groups": [a, b],
                        "label": pair["gold"],
                        "supplier": left.model_dump(),
                        "master": right.model_dump(),
                        "conflicts": conflicts(left, right),
                        "role": role,
                    }
                    if key in rows and rows[key]["label"] != value["label"]:
                        raise ValueError("conflicting development labels")
                    rows.setdefault(key, value)
    roles = {
        role: sorted([r for r in rows.values() if r["role"] == role], key=lambda r: order(r["id"]))
        for role in ("fit", "tune")
    }
    group_sets = {role: {g for r in values for g in r["groups"]} for role, values in roles.items()}
    if group_sets["fit"] & group_sets["tune"]:
        raise ValueError("fit/tuning entity leakage")
    x = {
        role: np.array(
            [feature_vector(Product(**r["supplier"]), Product(**r["master"])) for r in values]
        )
        for role, values in roles.items()
    }
    y = np.array([r["label"] for r in roles["fit"]])
    candidates = []
    best = None
    # Predeclared development-only search. No test/legacy qualification metrics select a model.
    for minimum in (10, 25):
        full = fit_trees(x["fit"], y, rounds=128, min_leaf=minimum)
        for rounds in (64, 96, 128):
            model = {**full, "trees": full["trees"][:rounds]}
            selected, count = thresholds(roles["tune"], predict(x["tune"], model))
            candidates.append(
                {"min_leaf": minimum, "trees": rounds, "selected": count, "thresholds": selected}
            )
            if best is None or count > best[0]:
                best = (count, model, selected, minimum)
    _, model, selected, minimum = best
    frozen = {
        "feature_version": feature_version(),
        "candidate_grid": candidates,
        "thresholds_frozen_from_tuning": selected,
        "role_pairs": {role: len(values) for role, values in roles.items()},
        "role_groups": {role: len(groups) for role, groups in group_sets.items()},
        "prior_wdc_qualification_reclassified_as_development": True,
        "model_sha256": digest(model),
        "source_sha256": sources,
        "new_qualification": "legacy: SHA256 entity groups <60; remaining groups reserved for challenge",
        "cross_source_physical_entity_independence_verified": False,
        "automatic_acceptance_enabled": False,
    }
    output.mkdir(parents=True)
    (output / "frozen.json").write_text(json.dumps(frozen, indent=2))
    legacy = corpus / "legacy-all.json.gz"
    sources[str(legacy)] = hashlib.sha256(legacy.read_bytes()).hexdigest()
    qualification = []
    challenge = []
    cross = 0
    excluded = 0
    for raw in map(json.loads, gzip.decompress(legacy.read_bytes()).splitlines()):
        try:
            pair = normalize_legacy_pair(raw)
        except ValueError:
            invalid += 1
            continue
        left, right = Product(**pair["input"]["supplier"]), Product(**pair["input"]["master"])
        if any(
            p.id in identities or digest([p.title.casefold(), p.brand.casefold()]) in texts
            for p in (left, right)
        ):
            excluded += 1
            continue
        groups = ["legacy:" + str(raw["cluster_id_" + s]) for s in ("left", "right")]
        masks = [int(order("cross-source-local-v1:" + g)[:8], 16) % 100 < 60 for g in groups]
        if masks[0] != masks[1]:
            cross += 1
            continue
        row = {
            "id": "#".join(sorted((left.id, right.id))),
            "offers": [left.id, right.id],
            "groups": groups,
            "label": pair["gold"],
            "supplier": left.model_dump(),
            "master": right.model_dump(),
            "conflicts": conflicts(left, right),
            "category": raw["category_left"],
        }
        (qualification if masks[0] else challenge).append(row)
    # Preserve the unscored challenge before qualification labels influence any decisions.
    challenge_dir = output / "challenge"
    challenge_dir.mkdir()
    for name, values in (
        ("inputs", [{k: r[k] for k in ("id", "supplier", "master")} for r in challenge]),
        ("gold", [{k: r[k] for k in ("id", "label", "groups", "category")} for r in challenge]),
    ):
        (challenge_dir / (name + ".jsonl")).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in values)
        )
    scores = predict(
        np.array(
            [
                feature_vector(Product(**r["supplier"]), Product(**r["master"]))
                for r in qualification
            ]
        ),
        model,
    )
    profile = {
        "version": feature_version(),
        **model,
        "negative_threshold": None,
        "positive_threshold": None,
        "qualification": {},
        "evidence_scope": "benchmark_review_drafts_only",
    }
    bands = {}
    for label, outcome in ((0, "different_product"), (1, "same_product")):
        threshold = selected[str(label)]
        if threshold is None:
            bands[outcome] = {"qualified": False, "reason": "no tuning band"}
            continue
        band = independent_band(qualification, scores, threshold, label)
        bands[outcome] = band
        if band["qualified"]:
            profile["negative_threshold" if label == 0 else "positive_threshold"] = threshold
            profile["qualification"][outcome] = {
                "samples": band["samples"],
                "correct": band["correct"],
            }
    if profile["qualification"]:
        verified = PairRouter(profile)
        (output / "profile.json").write_text(json.dumps(profile, indent=2))
        identity = verified.fingerprint
    else:
        identity = None
    report = {
        **frozen,
        "qualification": bands,
        "qualification_pairs": len(qualification),
        "challenge_pairs": len(challenge),
        "cross_role_legacy_pairs_excluded": cross,
        "source_identity_or_exact_text_overlap_excluded": excluded,
        "invalid_presentations": invalid,
        "source_sha256": sources,
        "profile_sha256": identity,
        "draft_profile_available": bool(identity),
        "test_or_challenge_used_for_fitting": False,
    }
    (output / "model-development.json").write_text(json.dumps(model, indent=2))
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    train(args.corpus, args.output)
