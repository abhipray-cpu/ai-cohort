"""Operator-authorized local corpus evaluation. No scraper; gold never enters runtime storage."""

import hashlib
import heapq
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from contracts.casecouncil import ROLES, Context, Proposal, Rights, Synthesis

from .consensus import digest
from .controller import Controller
from .evidence import extract, sha
from .store import Store

LABELS = ("uphold", "partial_uphold", "do_not_uphold")


def approve_development_subset(root, output, limit, max_calls, approval_reference):
    """Record explicit user approval in a new six-case-or-smaller research corpus.

    Operator tool, not an automatic grant or legal-permission oracle. The caller
    must possess actual user approval of the stated payload and model destination.
    Never mutate the broader source corpus or approve calibration/test records.
    """
    if not 1 <= limit <= 6 or not 22 <= max_calls <= 132 or len(approval_reference) < 20:
        raise ValueError("approval limited to six development cases and 132 cumulative calls")
    inventory = audit_corpus(root)
    if inventory["near_duplicate_warnings"]:
        raise ValueError("resolve split warnings first")
    root, manifest = load_manifest(root)
    selected = sorted(
        [r for r in manifest["cases"] if r["split"] == "development"], key=lambda r: digest(r["id"])
    )[:limit]
    if len(selected) != limit:
        raise ValueError("not enough approved development cases")
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    receipt = {
        "reference": approval_reference,
        "recorded": time.time(),
        "source_manifest_hash": inventory["manifest_hash"],
        "ids": [r["id"] for r in selected],
        "max_calls": max_calls,
        "destination": "model service configured through locally installed Codex",
        "scope": "six or fewer attributed development party-summary excerpts; no final outcomes in prompts; no UK certification",
    }
    for record in selected:
        for name, folder in [(d["path"], "inputs") for d in record["documents"]] + [
            (record["gold_path"], "gold")
        ]:
            source = safe_path(root, name, folder)
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    approved = {
        **manifest,
        "cases": selected,
        "egress_approval": receipt,
        "permission": {
            **manifest["permission"],
            "egress": True,
            "expires": min(manifest["permission"]["expires"], time.time() + 86400),
        },
    }
    (target / "manifest.json").write_text(json.dumps(approved, indent=2) + "\n")
    (target / "approval.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (target / "ATTRIBUTION.txt").write_text(
        manifest.get("attribution", "Source attribution retained in input packets.") + "\n"
    )
    audit_corpus(target)
    return receipt


def safe_path(root, name, folder):
    if not isinstance(name, str):
        raise TypeError("path required")
    target = (root / name).resolve()
    allowed = (root / folder).resolve()
    if not target.is_relative_to(allowed) or not target.is_file():
        raise ValueError("corpus path outside permitted root")
    return target


def load_manifest(root):
    root = Path(root).resolve()
    m = json.loads((root / "manifest.json").read_text())
    if m.get("schema_version") != 1 or not 1 <= len(m.get("cases", [])) <= 500:
        raise ValueError("corpus schema or size")
    right = Rights.model_validate(m["permission"])
    if right.expires <= time.time():
        raise ValueError("source authority not current")
    return root, m


def audit_corpus(root):
    root, m = load_manifest(root)
    ids = set()
    group_splits = {}
    exact = {}
    fingerprints = []
    warnings = []
    cohorts = {}
    for record in m["cases"]:
        cid = record["id"]
        group = record["group"]
        split = record["split"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]{5,80}", cid) or cid in ids:
            raise ValueError("duplicate or unsafe case id")
        if split not in {"development", "calibration", "test"}:
            raise ValueError("unknown split")
        if group in group_splits and group_splits[group] != split:
            raise ValueError("same dispute group crosses splits")
        group_splits[group] = split
        ids.add(cid)
        context = Context.model_validate(record["context"])
        cohort = record["cohort"]
        if cohort not in {"authored_fixture", "retrospective_decision", "prospective_case_file"}:
            raise ValueError("unknown cohort")
        cohorts[cohort] = cohorts.get(cohort, 0) + 1
        if not 1 <= len(record["documents"]) <= 20:
            raise ValueError("document count")
        nonpolicy = context.facts
        for doc in record["documents"]:
            path = safe_path(root, doc["path"], "inputs")
            raw = path.read_bytes()
            if sha(raw) != doc["sha256"]:
                raise ValueError("source digest mismatch")
            if doc["kind"] not in {"complaint", "policy", "correspondence", "other"}:
                raise ValueError("source kind")
            source = extract("audit", path.name, raw)
            if re.search(
                r"(?im)^\s*(?:my final decision|what i.ve decided|our investigator (?:upheld|did not uphold))",
                source["text"],
            ):
                raise ValueError("outcome-bearing source requires a reviewed label-free packet")
            if doc["kind"] != "policy":
                nonpolicy += "\n" + source["text"]
        normalized = " ".join(re.findall(r"\w+", nonpolicy.lower()))
        fingerprint = digest(normalized)
        if fingerprint in exact and exact[fingerprint] != group:
            raise ValueError("exact complaint duplicate uses a different group")
        exact[fingerprint] = group
        tokens = normalized.split()
        sample = set(
            heapq.nsmallest(
                128,
                {
                    hashlib.sha256(" ".join(tokens[n : n + 5]).encode()).digest()[:8]
                    for n in range(max(0, len(tokens) - 4))
                },
            )
        )
        for other_group, other_split, other_sample in fingerprints:
            if (
                group != other_group
                and split != other_split
                and len(sample) >= 32
                and len(sample & other_sample) / max(1, len(sample | other_sample)) >= 0.85
            ):
                warnings.append(
                    "Near-duplicate complaint groups cross splits: " + group + " / " + other_group
                )
        fingerprints.append((group, split, sample))
        gold = json.loads(safe_path(root, record["gold_path"], "gold").read_text())
        if set(gold.get("issues", {})) != {i.id for i in context.issues} or any(
            v not in LABELS for v in gold["issues"].values()
        ):
            raise ValueError("gold issue mapping invalid")
    return {
        "cases": len(ids),
        "groups": len(group_splits),
        "splits": {
            s: sum(c["split"] == s for c in m["cases"])
            for s in ("development", "calibration", "test")
        },
        "cohorts": cohorts,
        "manifest_hash": sha((root / "manifest.json").read_bytes()),
        "near_duplicate_warnings": warnings,
        "permission_status": "operator attestation present; not machine-verified legal permission",
        "model_egress_approved": m["permission"]["egress"],
        "real_data_validated": False,
        "full_product_accepted": False,
    }


class BaselineController(Controller):
    def __init__(self, store, provider, mode):
        super().__init__(store, provider)
        self.mode = mode

    def process(self, job):
        snapshot = json.loads(job["snapshot"])
        proposals = {}
        ballots = {}
        if self.mode == "vote_only":
            from contracts.casecouncil import Ballot

            from .consensus import aggregate, registry

            for role in ROLES:
                p = self.generate(job, "proposal:" + role, Proposal, snapshot)
                if p:
                    proposals[role] = p
            if len(proposals) == 3:
                r = registry(proposals, snapshot["binding"])
                for role in ROLES:
                    b = self.generate(
                        job,
                        "ballot:" + role,
                        Ballot,
                        snapshot,
                        {
                            "registry": r,
                            "proposals": proposals,
                            "baseline": "Independent proposals and voting, no critique or revision",
                        },
                    )
                    if b:
                        ballots[role] = b
                result = aggregate(
                    [i["id"] for i in snapshot["context"]["issues"]],
                    r,
                    ballots,
                    snapshot["blockers"],
                )
                predictions = {
                    i["issue_id"]: next(
                        c["disposition"] for c in r["candidates"] if c["id"] == i["winner"]
                    )
                    for i in result["issues"]
                    if i["qualified"]
                }
            else:
                result = None
                predictions = {}
        else:
            previous = None
            for n in range(10 if self.mode == "single_refine" else 1):
                previous = self.generate(
                    job,
                    "proposal:fairness" if n == 0 else f"proposal:fairness:refine_{n}",
                    Proposal,
                    snapshot,
                    {
                        "previous_own_proposal": previous,
                        "baseline": "Single reviewer, no peer proposals or ballots. Correct your own supported interpretation.",
                    },
                )
                if previous is None:
                    break
            if previous:
                proposals["fairness"] = previous
            result = None
            predictions = {
                i["issue_id"]: i["disposition"]
                for i in (previous or {}).get("issues", [])
                if i["disposition"] != "undetermined"
                and not i["missing"]
                and not snapshot["blockers"]
            }
        synthesis = (
            self.generate(
                job,
                "synthesis",
                Synthesis,
                snapshot,
                {
                    "proposals": proposals,
                    "baseline_mode": self.mode,
                    "computed_predictions": predictions,
                },
            )
            if proposals
            else None
        )
        self.store.finish(
            job,
            {
                "evaluation_mode": self.mode,
                "predictions": predictions,
                "proposals": proposals,
                "ballots": ballots,
                "consensus": result,
                "synthesis": synthesis,
                "review_requirements": ["evaluation_only"],
                "review_questions": {
                    "evaluation_only": "Benchmark baseline, not a multi-agent product decision."
                },
                "limitations": [
                    "Evaluation-only baseline. No human approval or calibrated confidence."
                ],
            },
            "draft_ready" if synthesis else "manual_required",
        )


def scores(results):
    pairs = [(g, r["predictions"].get(i)) for r in results for i, g in r["gold"].items()]
    f1 = {}
    for label in LABELS:
        tp = sum(g == label and p == label for g, p in pairs)
        fp = sum(g != label and p == label for g, p in pairs)
        fn = sum(g == label and p != label for g, p in pairs)
        f1[label] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    nonempty = [v for v in f1.values() if v is not None]
    return {
        "issues": len(pairs),
        "coverage": sum(p is not None for _, p in pairs) / len(pairs) if pairs else None,
        "per_class_f1": f1,
        "macro_f1_observed_classes": sum(nonempty) / len(nonempty) if nonempty else None,
        "independent_semantic_accuracy": "not_measured",
    }


def campaign(root, output, provider, mode, limit, max_calls, rights_reference, split="development"):
    if mode not in {"debate", "single", "vote_only", "single_refine"}:
        raise ValueError("unknown mode")
    if not 1 <= limit <= 500 or max_calls < 22 or len(rights_reference) < 20:
        raise ValueError("explicit bounded allowance and rights review required")
    inventory = audit_corpus(root)
    if inventory["near_duplicate_warnings"]:
        raise ValueError("resolve duplicate/split warnings before inference")
    root, m = load_manifest(root)
    if not m["permission"]["egress"]:
        raise ValueError("explicit model-egress approval missing")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    selected = sorted(
        [r for r in m["cases"] if r["split"] == split], key=lambda r: digest(r["id"])
    )[:limit]
    if not selected:
        raise ValueError("no eligible cases for selected split")
    (output / "selection.json").write_text(
        json.dumps(
            {
                "inventory": inventory,
                "ids": [r["id"] for r in selected],
                "mode": mode,
                "split": split,
                "max_calls": max_calls,
                "rights_review_reference": rights_reference,
                "limits": "22 reserved invocations required before scheduling each case; actual use can be lower",
            },
            indent=2,
        )
        + "\n"
    )
    store = Store(output / "service", evaluation_only=True)
    store.bootstrap("evaluator", secrets.token_urlsafe(24))
    w = store.create_workspace("evaluator", "Authorized isolated evaluation", "workspace")
    store.set_policy(
        "evaluator",
        w,
        1,
        {
            "name": "Frozen evaluation policy v1",
            "instructions": "Use only supplied evidence. Do not infer a published outcome or use external precedent. Respect the declared jurisdiction. Irish retrospective replay is not UK legal or prospective case-file validation. Party statements are allegations, not independent findings.",
            "required_documents": ["complaint"]
            if any(r["context"].get("jurisdiction") == "IE" for r in selected)
            else ["policy"],
            "egress_enabled": True,
        },
    )
    rid = store.add_rights("evaluator", w, m["permission"])
    results = []
    calls = 0
    for record in selected:
        if max_calls - calls < 22:
            break
        c = store.create_case("evaluator", w, record["context"], record["id"])["id"]
        for n, doc in enumerate(record["documents"]):
            path = safe_path(root, doc["path"], "inputs")
            store.add_source(
                "evaluator",
                c,
                n + 1,
                path.name,
                path.read_bytes(),
                doc["kind"],
                rid,
                "source" + str(n),
            )
        preview = store.preview("evaluator", c)
        j = store.start("evaluator", c, preview["binding"], "run")
        controller = (
            Controller(store, provider)
            if mode == "debate"
            else BaselineController(store, provider, mode)
        )
        controller.once()
        run = store.job("evaluator", j["id"])
        calls += run["calls"]
        packet = run["packet"] or {}
        predictions = packet.get("predictions", {})
        if mode == "debate" and packet.get("consensus"):
            candidates = {c["id"]: c for c in packet["registry"]["candidates"]}
            predictions = {
                i["issue_id"]: candidates[i["winner"]]["disposition"]
                for i in packet["consensus"]["issues"]
                if i["qualified"]
            }
        # Gold is opened only AFTER inference and is never written into runtime DB.
        gold = json.loads(safe_path(root, record["gold_path"], "gold").read_text())["issues"]
        results.append(
            {
                "id": record["id"],
                "group": record["group"],
                "cohort": record["cohort"],
                "job": j["id"],
                "state": run["state"],
                "calls": run["calls"],
                "predictions": predictions,
                "gold": gold,
                "unavailable": packet.get("unavailable", []),
                "packet_hash": run["packet_hash"],
            }
        )
        (output / "progress.json").write_text(json.dumps(results, indent=2) + "\n")
        if store.workspace("evaluator", w)["hold"]:
            break
    report = {
        "selected": len(selected),
        "completed": len(results),
        "calls": calls,
        "mode": mode,
        "metrics": scores(results),
        "results": results,
        "pending_ids": [r["id"] for r in selected if r["id"] not in {x["id"] for x in results}],
        "source_manifest_hash": inventory["manifest_hash"],
        "real_data_validated": False,
        "full_product_accepted": False,
        "limitations": [
            "Authority is operator-attested, not programmatically verified.",
            "Gold outcome comparison is not independent causal/next-step review.",
            "Authored fixtures never establish real-data accuracy.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
