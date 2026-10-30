"""SHA-256 helpers for raw frame bytes and whole files."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

_CHUNK = 1 << 20  # 1 MiB


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 digest of a single frame's raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Union[str, Path]) -> str:
    """Hex SHA-256 digest of a whole file, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()
