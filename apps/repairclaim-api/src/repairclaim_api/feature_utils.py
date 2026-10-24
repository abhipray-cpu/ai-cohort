"""Canonical identities for durable casework; no sensitive values in audit messages."""

import hashlib
import json
from uuid import uuid4


def identifier():
    return uuid4().hex


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()
