import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

ANALYSIS_VERSION = "clausegate-2-full-context-exact-quotes"


def now():
    return datetime.now(UTC).isoformat()


def later(seconds):
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()


def ident():
    return secrets.token_hex(16)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def byte_hash(raw):
    return hashlib.sha256(raw).hexdigest()


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(UTC).isoformat()
