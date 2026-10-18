"""Bounded, JSON-only local pair scorer for review drafts, never automatic links."""

import hashlib
import json
import math
import os
import re
import unicodedata
from pathlib import Path

from contracts.catalogbridge import Citation, Proposal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .matching import conflicts, digest, validate_proposal, words


def feature_version():
    return digest(
        {
            "algorithm": "lexical-pair-gbdt-v1",
            "source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "matching": hashlib.sha256(
                Path(__file__).with_name("matching.py").read_bytes()
            ).hexdigest(),
        }
    )


def overlap(a, b):
    return len(a & b) / max(1, len(a | b))


def feature_vector(left, right):
    """Symmetric source-text-only features; IDs, labels and price cannot leak."""
    a, b = words(left.title), words(right.title)
    normalized = [
        re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", p.title).casefold())
        for p in (left, right)
    ]
    x, y = normalized
    grams = lambda s, n: {s[i : i + n] for i in range(max(0, len(s) - n + 1))}
    numbers = [set(re.findall(r"\d+(?:\.\d+)?", p.title)) for p in (left, right)]
    codes = [
        {w for w in terms if any(c.isdigit() for c in w) and any(c.isalpha() for c in w)}
        for terms in (a, b)
    ]
    shared = a & b
    clash = set(conflicts(left, right))
    brands = [re.sub(r"[\W_]+", "", p.brand.casefold()) for p in (left, right)]
    jaccard = overlap(a, b)
    return [
        jaccard,
        jaccard * jaccard,
        len(shared) / max(1, min(len(a), len(b))),
        min(len(a), len(b)) / max(1, max(len(a), len(b))),
        min(len(x), len(y)) / max(1, max(len(x), len(y))),
        float(bool(x) and x == y),
        overlap(grams(x, 3), grams(y, 3)),
        overlap(grams(x, 4), grams(y, 4)),
        overlap(*numbers),
        float(bool(numbers[0]) and numbers[0] == numbers[1]),
        float(bool(numbers[0]) and bool(numbers[1])),
        overlap(*codes),
        float(bool(codes[0]) and codes[0] == codes[1]),
        float(bool(codes[0]) and bool(codes[1])),
        float(bool(brands[0]) and brands[0] == brands[1]),
        float(bool(brands[0]) and bool(brands[1])),
        min(1.0, max((len(w) for w in shared), default=0) / 20),
        *[
            float(k in clash)
            for k in ("capacity", "form_factor", "pack", "condition", "brand", "model")
        ],
        float(bool(clash)),
    ]


def lower_bound(correct, samples):
    if not samples:
        return 0.0
    z = 1.959963984540054
    p = correct / samples
    return (
        p
        + z * z / (2 * samples)
        - z * math.sqrt(p * (1 - p) / samples + z * z / (4 * samples * samples))
    ) / (1 + z * z / samples)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Node(Strict):
    feature: int | None = Field(default=None, ge=0, lt=24)
    threshold: float | None = Field(default=None, ge=0, le=1)
    left: "Node | None" = None
    right: "Node | None" = None
    value: float | None = Field(default=None, ge=-20, le=20)

    @model_validator(mode="after")
    def complete(self):
        if self.value is not None:
            if any(x is not None for x in (self.feature, self.threshold, self.left, self.right)):
                raise ValueError("mixed leaf and branch")
        elif any(x is None for x in (self.feature, self.threshold, self.left, self.right)):
            raise ValueError("incomplete branch")
        return self


class Band(Strict):
    samples: int = Field(ge=500)
    correct: int = Field(ge=0)

    @model_validator(mode="after")
    def qualified(self):
        if self.correct > self.samples or lower_bound(self.correct, self.samples) < 0.99:
            raise ValueError("unqualified confidence band")
        return self


class Profile(Strict):
    version: str
    bias: float = Field(ge=-20, le=20)
    learning_rate: float = Field(gt=0, le=1)
    trees: list[Node] = Field(max_length=128)
    negative_threshold: float | None = Field(default=None, gt=0, le=0.1)
    positive_threshold: float | None = Field(default=None, ge=0.9, lt=1)
    qualification: dict[str, Band]
    evidence_scope: str

    @model_validator(mode="after")
    def supported(self):
        if (
            self.version != feature_version()
            or self.evidence_scope != "benchmark_review_drafts_only"
        ):
            raise ValueError("stale or unsupported routing profile")
        expected = set()
        if self.negative_threshold is not None:
            expected.add("different_product")
        if self.positive_threshold is not None:
            expected.add("same_product")
        if not expected or set(self.qualification) != expected:
            raise ValueError("confidence-band evidence required")

        def check(node, depth=0):
            if depth > 3:
                raise ValueError("tree exceeds depth bound")
            if node.value is None:
                check(node.left, depth + 1)
                check(node.right, depth + 1)

        for tree in self.trees:
            check(tree)
        return self


class PairRouter:
    def __init__(self, body):
        self.profile = Profile.model_validate(body)
        self.fingerprint = digest(self.profile.model_dump())

    def score(self, left, right):
        features = feature_vector(left, right)
        logit = self.profile.bias
        for node in self.profile.trees:
            while node.value is None:
                node = node.left if features[node.feature] <= node.threshold else node.right
            logit += self.profile.learning_rate * node.value
        return 1 / (1 + math.exp(-max(-40, min(40, logit))))

    def propose(self, supplier, gallery):
        if (
            not gallery
            or len(gallery) > 10
            or any(len(p.title) > 2000 or len(p.brand) > 1000 for p in [supplier, *gallery])
        ):
            return None
        scores = [(self.score(supplier, row), row) for row in gallery]
        positive = [
            (s, row)
            for s, row in scores
            if self.profile.positive_threshold is not None and s >= self.profile.positive_threshold
        ]
        negative = self.profile.negative_threshold
        if len(positive) == 1 and all(
            row.id == positive[0][1].id or (negative is not None and s <= negative)
            for s, row in scores
        ):
            score, candidate = positive[0]
            outcome = "same_product"
        elif negative is not None and all(s <= negative for s, _ in scores):
            score, candidate = max(scores, key=lambda item: item[0])
            outcome = "different_product"
        else:
            return None
        proposal = Proposal(
            candidate_id=candidate.id,
            outcome=outcome,
            reason="Local qualified benchmark band; review required. No model call dispatched.",
            evidence=[
                Citation(side="supplier", field="title", quote=supplier.title[:160]),
                Citation(side="candidate", field="title", quote=candidate.title[:160]),
            ],
        )
        try:
            validate_proposal(proposal, supplier, gallery)
        except ValueError:
            return None
        band = self.profile.qualification[outcome]
        return proposal, {
            "profile_sha256": self.fingerprint,
            "raw_score": score,
            "band_samples": band.samples,
            "band_precision_lower_bound": lower_bound(band.correct, band.samples),
            "evidence_scope": self.profile.evidence_scope,
            "automatic_acceptance": False,
            "candidate_scores": {row.id: s for s, row in scores},
        }


def configured_router():
    path = os.environ.get("CATALOGBRIDGE_ROUTER_PROFILE")
    if not path:
        raise ValueError("local routing profile not configured")
    with Path(path).open("rb") as stream:
        payload = stream.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("local routing profile exceeds envelope")
    return PairRouter(json.loads(payload))
