"""Freeze a local review-draft scorer using development splits only; never test gold."""

import argparse
import hashlib
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from catalogbridge_api.corpus import normalize_pair, safe_members
from catalogbridge_api.local_router import PairRouter, feature_vector, feature_version, lower_bound
from catalogbridge_api.matching import conflicts, digest
from contracts.catalogbridge import Product

from scripts.audit_catalogbridge_corpus import load_rows


def order(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def group_role(left, right):
    def role(value):
        bucket = int(order("local-router-v1:" + str(value))[:8], 16) % 100
        return "fit" if bucket < 35 else "tune" if bucket < 50 else "qualification"

    return role(left) if role(left) == role(right) else None


def sigmoid(value):
    return 1 / (1 + np.exp(-np.clip(value, -40, 40)))


def tree_values(x, node):
    if "value" in node:
        return np.full(len(x), node["value"])
    mask = x[:, node["feature"]] <= node["threshold"]
    result = np.empty(len(x))
    result[mask] = tree_values(x[mask], node["left"])
    result[~mask] = tree_values(x[~mask], node["right"])
    return result


def predict(x, model):
    logit = np.full(len(x), model["bias"])
    for tree in model["trees"]:
        logit += model["learning_rate"] * tree_values(x, tree)
    return sigmoid(logit)


def fit_trees(x, y, rounds=96, min_leaf=25):
    """Small deterministic Newton-boosted depth-three trees, exported as JSON."""
    probability = float(np.clip(y.mean(), 0.001, 0.999))
    bias = math.log(probability / (1 - probability))
    model = {"bias": bias, "learning_rate": 0.15, "trees": []}
    cuts = [np.unique(np.quantile(x[:, f], np.linspace(0, 1, 17)))[1:-1] for f in range(x.shape[1])]
    # Binary features need the separating boundary, too.
    cuts = [
        np.unique(np.r_[cut, (x[:, f].min() + x[:, f].max()) / 2]) for f, cut in enumerate(cuts)
    ]
    bins = [np.searchsorted(cut, x[:, f], side="left") for f, cut in enumerate(cuts)]
    logit = np.full(len(x), bias)
    regularization = 5.0
    for _ in range(rounds):
        p = sigmoid(logit)
        gradient = y - p
        hessian = p * (1 - p)

        def build(indices, depth=0, gradient=gradient, hessian=hessian):
            g = float(gradient[indices].sum())
            h = float(hessian[indices].sum())
            leaf = {"value": float(np.clip(g / (h + regularization), -5, 5))}
            if depth == 3 or len(indices) < 2 * min_leaf:
                return leaf
            best = None
            best_gain = 1e-6
            for feature, cut in enumerate(cuts):
                size = len(cut) + 1
                counts = np.cumsum(np.bincount(bins[feature][indices], minlength=size))[:-1]
                gs = np.cumsum(
                    np.bincount(bins[feature][indices], weights=gradient[indices], minlength=size)
                )[:-1]
                hs = np.cumsum(
                    np.bincount(bins[feature][indices], weights=hessian[indices], minlength=size)
                )[:-1]
                gains = (
                    gs * gs / (hs + regularization)
                    + (g - gs) ** 2 / (h - hs + regularization)
                    - g * g / (h + regularization)
                )
                gains[(counts < min_leaf) | (len(indices) - counts < min_leaf)] = -np.inf
                if len(gains):
                    chosen = int(np.argmax(gains))
                    if gains[chosen] > best_gain:
                        best_gain = float(gains[chosen])
                        best = (feature, float(cut[chosen]))
            if best is None:
                return leaf
            feature, threshold = best
            mask = x[indices, feature] <= threshold
            return {
                "feature": feature,
                "threshold": threshold,
                "left": build(indices[mask], depth + 1),
                "right": build(indices[~mask], depth + 1),
            }

        tree = build(np.arange(len(x)))
        model["trees"].append(tree)
        logit += model["learning_rate"] * tree_values(x, tree)
    return model


def independent_band(rows, scores, threshold, label):
    used = set()
    selected = []
    for index in sorted(range(len(rows)), key=lambda i: order(rows[i]["id"])):
        row = rows[index]
        eligible = scores[index] >= threshold if label else scores[index] <= threshold
        if label and row["conflicts"]:
            eligible = False
        if not eligible or set(row["offers"]) & used:
            continue
        selected.append(row)
        used.update(row["offers"])
    correct = sum(r["label"] == label for r in selected)
    groups = Counter(g for r in selected for g in set(r["groups"]))
    bound = lower_bound(correct, len(selected))
    return {
        "samples": len(selected),
        "correct": correct,
        "precision_lower_bound": bound,
        "qualified": len(selected) >= 500 and bound >= 0.99,
        "internal_offer_overlap": 0,
        "entity_groups": len(groups),
        "reused_entity_groups": sum(n > 1 for n in groups.values()),
        "selected_id_sha256": digest(sorted(r["id"] for r in selected)),
        "disagreement_ids": [r["id"] for r in selected if r["label"] != label],
    }


def train(corpus, output):
    if output.exists():
        raise ValueError("preserve previous evidence")
    output.mkdir(parents=True)
    rows = {}
    sources = {}
    invalid = []
    overlap = 0
    cross_role = 0
    for hard in (20, 50, 80):
        path = corpus / f"{hard}pair.zip"
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with zipfile.ZipFile(path) as archive:
            safe_members(archive)
            for member in archive.namelist():
                if "train_large" not in member and "valid_large" not in member:
                    continue
                for position, raw in enumerate(load_rows(archive, member)):
                    try:
                        pair = normalize_pair(raw)
                    except ValueError:
                        invalid.append({"member": member, "row": position})
                        continue
                    left, right = (
                        Product(**pair["input"]["supplier"]),
                        Product(**pair["input"]["master"]),
                    )
                    groups = [str(raw["cluster_id_left"]), str(raw["cluster_id_right"])]
                    role = group_role(*groups)
                    if role is None:
                        cross_role += 1
                        continue
                    if role == "fit" and "valid_large" in member:
                        continue  # Official validation rows never fit model parameters.
                    key = "#".join(sorted((left.id, right.id)))
                    value = {
                        "id": key,
                        "offers": [left.id, right.id],
                        "groups": groups,
                        "role": role,
                        "label": pair["gold"],
                        "supplier": left.model_dump(),
                        "master": right.model_dump(),
                        "conflicts": conflicts(left, right),
                    }
                    if key in rows:
                        if rows[key]["label"] != value["label"]:
                            raise ValueError("conflicting development labels")
                        overlap += 1
                    rows.setdefault(key, value)
    roles = {
        role: sorted([r for r in rows.values() if r["role"] == role], key=lambda r: order(r["id"]))
        for role in ("fit", "tune", "qualification")
    }
    groups = {role: {g for r in values for g in r["groups"]} for role, values in roles.items()}
    offers = {role: {g for r in values for g in r["offers"]} for role, values in roles.items()}
    for a, b in (("fit", "tune"), ("fit", "qualification"), ("tune", "qualification")):
        if groups[a] & groups[b] or offers[a] & offers[b]:
            raise ValueError("development split leakage")
    x = {
        role: np.array(
            [feature_vector(Product(**r["supplier"]), Product(**r["master"])) for r in values]
        )
        for role, values in roles.items()
    }
    y = np.array([r["label"] for r in roles["fit"]])
    model = fit_trees(x["fit"], y)
    tune = predict(x["tune"], model)
    thresholds = {}
    tuning_grid = {}
    for label, grid in (
        (0, (0.001, 0.005, 0.01, 0.02, 0.05, 0.1)),
        (1, (0.9, 0.95, 0.98, 0.99, 0.995, 0.999)),
    ):
        choices = []
        for threshold in grid:
            # Threshold selection is development-only; qualification is read once afterwards.
            selected = [
                i
                for i, r in enumerate(roles["tune"])
                if (tune[i] >= threshold if label else tune[i] <= threshold)
                and (not label or not r["conflicts"])
            ]
            correct = sum(roles["tune"][i]["label"] == label for i in selected)
            tuning_grid[f"{label}:{threshold}"] = {
                "selected": len(selected),
                "correct": correct,
                "lower_bound": lower_bound(correct, len(selected)),
            }
            # Tuning chooses a candidate; only the untouched qualification
            # partition can certify >=500 cases and a >=99% lower bound.
            if len(selected) >= 100 and correct / len(selected) >= 0.995:
                choices.append((len(selected), threshold))
        thresholds[str(label)] = max(choices)[1] if choices else None
    frozen = {
        "feature_version": feature_version(),
        "source_sha256": sources,
        "split_seed": "local-router-v1",
        "role_pairs": {k: len(v) for k, v in roles.items()},
        "role_groups": {k: len(v) for k, v in groups.items()},
        "role_offer_hashes": {k: digest(sorted(v)) for k, v in offers.items()},
        "cross_role_group_or_offer_overlap": 0,
        "test_gold_read": False,
        "thresholds_frozen_from_tuning": thresholds,
        "model_sha256": digest(model),
    }
    (output / "frozen.json").write_text(json.dumps(frozen, indent=2))
    qualification_scores = predict(x["qualification"], model)
    qualification = {}
    profile = {
        "version": feature_version(),
        **model,
        "negative_threshold": None,
        "positive_threshold": None,
        "qualification": {},
        "evidence_scope": "benchmark_review_drafts_only",
    }
    for label, outcome in ((0, "different_product"), (1, "same_product")):
        threshold = thresholds[str(label)]
        if threshold is None:
            qualification[outcome] = {"qualified": False, "reason": "no tuning threshold qualified"}
            continue
        band = independent_band(roles["qualification"], qualification_scores, threshold, label)
        qualification[outcome] = band
        if band["qualified"]:
            profile["negative_threshold" if label == 0 else "positive_threshold"] = threshold
            profile["qualification"][outcome] = {
                "samples": band["samples"],
                "correct": band["correct"],
            }
    active = bool(profile["qualification"])
    if active:
        PairRouter(profile)
        (output / "profile.json").write_text(json.dumps(profile, indent=2))
    (output / "model-development.json").write_text(json.dumps(model, indent=2))
    report = {
        **frozen,
        "qualification": qualification,
        "draft_profile_available": active,
        "independently_adjudicated_auto_acceptance_qualified": False,
        "cluster_reuse_prevents_independent_sample_claim": True,
        "invalid_development_presentations": len(invalid),
        "duplicate_pair_presentations": overlap,
        "cross_role_pair_presentations_excluded": cross_role,
        "profile_sha256": PairRouter(profile).fingerprint if active else None,
        "automatic_acceptance_enabled": False,
        "tuning_grid": tuning_grid,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    train(args.corpus, args.output)
