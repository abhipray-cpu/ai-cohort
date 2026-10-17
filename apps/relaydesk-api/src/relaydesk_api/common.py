import hashlib
import json
import uuid
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


def ident():
    return uuid.uuid4().hex


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
