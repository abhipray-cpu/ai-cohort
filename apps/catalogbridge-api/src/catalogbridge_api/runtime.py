"""Safe failure evidence and explicit pre-dispatch refusals; never retain raw logs."""

import hashlib
import json
import re
from uuid import UUID


def receipt_evidence(value):
    """Whitelist bounded metadata at persistence, even for an injected adapter."""
    value = value if isinstance(value, dict) else {}
    categories = {
        "ok",
        "runtime_failure",
        "timeout",
        "quota",
        "rate_limit",
        "authentication",
        "network",
        "model_unavailable",
        "restricted_tool",
        "audit_unverified",
        "usage_unknown",
        "dispatch_not_started",
    }
    category = value.get("category")
    clean = {
        "category": category
        if isinstance(category, str) and category in categories
        else "runtime_failure"
    }
    for key in ("exit_code", "stdout_bytes", "stderr_bytes"):
        item = value.get(key)
        if type(item) is int and abs(item) < 2**63 and (key == "exit_code" or item >= 0):
            clean[key] = item
    for key in ("stdout_sha256", "stderr_sha256"):
        item = value.get(key)
        if isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item):
            clean[key] = item
    threads = value.get("runtime_thread_ids")
    clean["runtime_thread_ids"] = []
    for item in threads[:4] if isinstance(threads, list) else []:
        try:
            thread = str(UUID(item)) if isinstance(item, str) else None
        except ValueError:
            thread = None
        if thread and thread not in clean["runtime_thread_ids"]:
            clean["runtime_thread_ids"].append(thread)
    return clean


def diagnostics(stdout="", stderr="", *, exit_code=None, exception=None):
    stdout_raw = stdout if isinstance(stdout, bytes) else (stdout or "").encode()
    stderr_raw = stderr if isinstance(stderr, bytes) else (stderr or "").encode()
    stdout = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout or ""
    stderr = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr or ""
    errors = []
    threads = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") in {"error", "turn.failed"}:
            errors.append(json.dumps(event))
        if isinstance(event, dict) and event.get("type") == "thread.started":
            value = event.get("thread_id")
            try:
                thread = str(UUID(value)) if isinstance(value, str) else None
            except ValueError:
                thread = None
            if thread and thread not in threads and len(threads) < 4:
                threads.append(thread)
    text = ("\n".join(errors) + "\n" + stderr).casefold()
    category = "ok" if exit_code == 0 else "runtime_failure"
    for name, markers in {
        "quota": ("usage_limit", "usage limit", "insufficient_quota"),
        "rate_limit": ("rate_limit", "rate limit", "too many requests"),
        "authentication": ("authentication_error", "unauthorized", "token expired"),
        "network": (
            "connection reset",
            "connection refused",
            "network is unreachable",
            "dns error",
        ),
        "model_unavailable": ("model_not_found", "model is not supported"),
    }.items():
        if any(marker in text for marker in markers):
            category = name
            break
    if exception:
        category = "timeout" if "timeout" in type(exception).__name__.casefold() else category
    return {
        "category": category,
        "exit_code": exit_code,
        "stdout_bytes": len(stdout_raw),
        "stderr_bytes": len(stderr_raw),
        "stdout_sha256": hashlib.sha256(stdout_raw).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr_raw).hexdigest(),
        "runtime_thread_ids": threads,
    }


class ProviderFailure(ValueError):
    def __init__(self, evidence, usage=None):
        super().__init__("provider runtime failed: " + evidence["category"])
        self.diagnostics = evidence
        self.usage = usage


class DispatchNotStarted(ProviderFailure):
    def __init__(self):
        from contracts.catalogbridge import Usage

        super().__init__(
            {"category": "dispatch_not_started"}, Usage(input_tokens=0, output_tokens=0)
        )
