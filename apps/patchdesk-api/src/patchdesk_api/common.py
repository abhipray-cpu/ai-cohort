import hashlib
import json
import uuid
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def identifier():
    return uuid.uuid4().hex
