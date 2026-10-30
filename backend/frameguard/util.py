"""Small shared helpers: canonical JSON, hashing, and the project error type."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


class FrameGuardError(Exception):
    """Raised for any expected, user-facing failure in the pipeline."""


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON encoding used for anything that gets hashed.

    Keys are sorted and whitespace is stripped so that the same logical object
    always produces the same bytes (and therefore the same hash).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
