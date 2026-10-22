"""Pure deterministic metrics, failure rules and fixed-look analysis."""

import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from statistics import NormalDist

import numpy as np
from pydantic import BaseModel


def canonical(value):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value):
    return hashlib.sha256(
        value if isinstance(value, bytes) else canonical(value).encode()
    ).hexdigest()


def assignment(scope, session, seed, weight):
    if type(weight) is not int or not 0 <= weight <= 100:
        raise ValueError("invalid weight")
    bucket = int(digest([scope, session, seed])[:16], 16) % 10000
    return "candidate" if bucket < weight * 100 else "stable"


def unique(events):
    result = {}
    for event in events:
        if event.id in result and result[event.id] != event:
            raise ValueError("conflicting event identity")
        result[event.id] = event
    return sorted(result.values(), key=lambda e: (e.at, e.sequence, e.id))


def quantile(values, q):
    return float(np.quantile(values, q)) if values else None


def scoped_events(rows):
    from contracts.releasefence import Event

    result = []
    for row in rows:
        event = Event.model_validate(row["event"])
        scope = row["enrollment"]
        result.append(
            event.model_copy(
                update={
                    "id": digest([scope, event.id]),
                    "task": digest([scope, event.task]),
                    "session": digest([scope, event.session]),
                    "usage": event.usage.model_copy(
                        update={"attempt": digest([scope, event.usage.attempt])}
                    )
                    if event.usage
                    else None,
                }
            )
        )
    return result


def metrics(events):
    tasks = defaultdict(list)
    for event in unique(events):
        tasks[event.task].append(event)
    accepted = closed = successful = failed = unknown = expected = 0
    known = Decimal(0)
    estimated = Decimal(0)
    durations = []
    observations = []
    usages = {}
    orphans = 0
    for task, rows in tasks.items():
        starts = [e for e in rows if e.kind == "accepted"]
        ends = [e for e in rows if e.kind == "terminal"]
        if len(starts) > 1 or len(ends) > 1:
            raise ValueError("ambiguous task lifecycle")
        if not starts:
            orphans += len(rows)
            continue
        if any(e.release != starts[0].release or e.session != starts[0].session for e in rows):
            raise ValueError("task identity changed")
        accepted += 1
        end = ends[0] if ends else None
        if end and end.at < starts[0].at:
            raise ValueError("terminal before acceptance")
        closed += bool(end)
        successful += bool(end and end.outcome == "success")
        failed += bool(end and end.outcome != "success")
        local = Decimal(0)
        local_unknown = False
        local_attempts = set()
        for e in rows:
            if e.usage is None or e.usage.inclusive:
                continue
            u = e.usage
            if u.attempt in usages and usages[u.attempt] != (task, u):
                raise ValueError("conflicting model attempt")
            if u.attempt in local_attempts:
                continue
            local_attempts.add(u.attempt)
            usages[u.attempt] = (task, u)
            if u.reported_cost is not None:
                known += u.reported_cost
                local += u.reported_cost
            elif u.estimated_cost is not None:
                estimated += u.estimated_cost
                local += u.estimated_cost
            else:
                unknown += 1
                local_unknown = True
        calls = end.model_calls if end else max(1, len(local_attempts))
        if calls < len(local_attempts):
            raise ValueError("usage exceeds terminal call counter")
        missing = calls - len(local_attempts)
        unknown += missing
        expected += calls
        if end and end.duration_ms is not None:
            durations.append(end.duration_ms)
            observations.append(
                {
                    "session": starts[0].session,
                    "success": end.outcome == "success",
                    "duration_ms": end.duration_ms,
                    "cost": None if local_unknown or missing else str(local),
                }
            )
    tokens = {}
    for field in ("input_tokens", "cached_input_tokens", "output_tokens"):
        values = [getattr(u, field) for _, u in usages.values()]
        tokens[field] = (
            sum(values) if len(values) == expected and all(v is not None for v in values) else None
        )
    tokens["uncached_input_tokens"] = (
        tokens["input_tokens"] - tokens["cached_input_tokens"]
        if tokens["input_tokens"] is not None and tokens["cached_input_tokens"] is not None
        else None
    )
    return {
        **tokens,
        "accepted": accepted,
        "completed": closed,
        "successful": successful,
        "failed": failed,
        "coverage": closed / accepted if accepted else None,
        "p50_ms": quantile(durations, 0.5),
        "p95_ms": quantile(durations, 0.95),
        "known_cost": str(known),
        "estimated_cost": str(estimated),
        "unknown_calls": unknown,
        "model_calls": expected,
        "orphan_events": orphans,
        "cost_per_success": str((known + estimated) / successful)
        if successful and not unknown and closed == accepted
        else None,
        "observations": observations,
        "latency_missing": closed - len(durations),
    }


def _wilson(failed, n, z):
    p = failed / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    delta = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, center - delta), min(1, center + delta)


def analyze(stable, candidate, policy, *, coverage=1.0):
    result = {
        "method": "fixed-looks-v1",
        "seed": 20261021,
        "decision": "inconclusive",
        "reasons": [],
        "n_stable": len(stable),
        "n_candidate": len(candidate),
    }
    if min(len(stable), len(candidate)) < policy.minimum_sessions:
        result["reasons"] = ["insufficient_sessions"]
        return result
    if len(stable) > 10000 or len(candidate) > 10000:
        result["reasons"] = ["analysis_capacity"]
        return result
    if coverage is None or coverage < policy.coverage:
        result["reasons"] = ["incomplete_lifecycle"]
        return result
    for arm in (stable, candidate):
        if len({r["session"] for r in arm}) != len(arm):
            result["reasons"] = ["dependent_sessions"]
            return result
        if any(r["cost"] is None or r["duration_ms"] is None for r in arm):
            result["reasons"] = ["unavailable_cost_or_latency"]
            return result
    if {r["session"] for r in stable} & {r["session"] for r in candidate}:
        result["reasons"] = ["cross_arm_session_overlap"]
        return result
    # Three metrics x two planned analysis looks (5%,25%), two component intervals.
    tail = policy.alpha / 24
    z = NormalDist().inv_cdf(1 - tail)
    a = _wilson(sum(not r["success"] for r in stable), len(stable), z)
    b = _wilson(sum(not r["success"] for r in candidate), len(candidate), z)
    bounds = {"failure_difference": [b[0] - a[1], b[1] - a[0]]}
    rng = np.random.default_rng(result["seed"])
    sampled = []
    for arm in (stable, candidate):
        latency = np.asarray([r["duration_ms"] for r in arm], dtype=float)
        cost = np.asarray([float(r["cost"]) for r in arm], dtype=float)
        success = np.asarray([r["success"] for r in arm], dtype=int)
        if (
            not np.isfinite(latency).all()
            or not np.isfinite(cost).all()
            or (cost < 0).any()
            or (latency < 0).any()
        ):
            raise ValueError("invalid analysis samples")
        lat = []
        cps = []
        for _ in range(2000):
            idx = rng.integers(0, len(arm), size=len(arm))
            count = success[idx].sum()
            if not count:
                result["reasons"] = ["zero_success_resample"]
                return result
            lat.append(float(np.quantile(latency[idx], 0.95)))
            cps.append(float(cost[idx].sum() / count))
        sampled.append((np.asarray(lat), np.asarray(cps)))
    for i, name in enumerate(("p95_ratio", "cost_success_ratio")):
        base = sampled[0][i]
        cand = sampled[1][i]
        if (base <= 0).any():
            result["reasons"] = ["zero_baseline"]
            return result
        bounds[name] = [float(x) for x in np.quantile(cand / base, [tail, 1 - tail])]
    margins = {
        "failure_difference": policy.failure_margin,
        "p95_ratio": 1 + policy.latency_margin,
        "cost_success_ratio": 1 + policy.cost_margin,
    }
    result["bounds"] = bounds
    failed = [name for name, bound in bounds.items() if bound[0] > margins[name]]
    passed = all(bound[1] <= margins[name] for name, bound in bounds.items())
    result.update(
        decision="fail" if failed else "pass" if passed else "inconclusive",
        reasons=failed or ([] if passed else ["uncertain_noninferiority"]),
    )
    return result


def detect(events, policy, *, now):
    tasks = defaultdict(list)
    findings = []
    for e in unique(events):
        tasks[e.task].append(e)
    for task, rows in tasks.items():
        accepted = next((e for e in rows if e.kind == "accepted"), None)
        if not accepted:
            continue
        base = {"task": task, "release": accepted.release, "session": accepted.session}
        ends = [e for e in rows if e.kind == "terminal"]
        for e in rows:
            if e.iteration is not None and e.iteration > policy.max_iterations:
                findings.append(
                    {
                        **base,
                        "rule": "iteration_limit_exceeded",
                        "severity": "critical",
                        "event": e.id,
                    }
                )
            if e.stop_reason in {"iteration_exhausted", "deadline", "schema_exhausted"}:
                findings.append(
                    {**base, "rule": e.stop_reason, "severity": "critical", "event": e.id}
                )
        if (
            not ends
            and now
            > max(
                accepted.at + policy.deadline_seconds,
                max((e.waiting_until or 0 for e in rows), default=0),
            )
            + policy.lateness_seconds
        ):
            findings.append(
                {**base, "rule": "missing_terminal", "severity": "warning", "event": accepted.id}
            )
        last = None
        count = 0
        for e in rows:
            if e.kind != "tool" or e.polling or not e.tool_fingerprint:
                continue
            key = (e.tool_fingerprint, e.progress)
            count = count + 1 if key == last else 1
            last = key
            if count == policy.repeated_calls:
                findings.append(
                    {**base, "rule": "repeated_action", "severity": "warning", "event": e.id}
                )
    return findings
