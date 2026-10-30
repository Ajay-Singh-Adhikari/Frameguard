"""A local, append-only, hash-chained ledger that stands in for the blockchain.

Each anchor record carries the hash of the previous record, so the file behaves
like a miniature chain: you cannot alter or remove a past entry without breaking
every ``entry_hash`` that follows. This is the zero-setup default anchor; the
Solidity ``VideoRegistry`` contract is the production counterpart.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from .util import FrameGuardError, canonical_json, sha256_hex, utc_now_iso

_GENESIS = "0" * 64


class LocalLedger:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    # --- persistence ---
    def _load(self) -> Dict[str, List[dict]]:
        if not self.path.exists():
            return {"anchors": [], "log": []}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, List[dict]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)  # atomic
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    @staticmethod
    def _hash_entry(record: dict) -> str:
        body = {k: v for k, v in record.items() if k != "entry_hash"}
        return sha256_hex(canonical_json(body))

    # --- registry interface (shared with the on-chain client) ---
    def register(self, anchor: dict) -> dict:
        data = self._load()
        if any(a["video_id"] == anchor["video_id"] for a in data["anchors"]):
            raise FrameGuardError(f"video_id '{anchor['video_id']}' is already registered")

        prev_hash = data["anchors"][-1]["entry_hash"] if data["anchors"] else _GENESIS
        record = {
            **anchor,
            "index": len(data["anchors"]),
            "prev_hash": prev_hash,
            "backend": "local-ledger",
        }
        record["entry_hash"] = self._hash_entry(record)
        data["anchors"].append(record)
        data["log"].append({
            "video_id": anchor["video_id"],
            "action": "Registered",
            "actor": anchor.get("registrant", "local"),
            "timestamp": utc_now_iso(),
        })
        self._save(data)
        return record

    def get(self, video_id: str) -> Optional[dict]:
        for a in self._load()["anchors"]:
            if a["video_id"] == video_id:
                return a
        return None

    def log_verification(self, video_id: str, root_matched: bool, actor: str = "local") -> None:
        data = self._load()
        data["log"].append({
            "video_id": video_id,
            "action": "Verified",
            "root_matched": root_matched,
            "actor": actor,
            "timestamp": utc_now_iso(),
        })
        self._save(data)

    # --- integrity of the ledger itself ---
    def verify_chain(self) -> bool:
        prev = _GENESIS
        for record in self._load()["anchors"]:
            if record.get("prev_hash") != prev:
                return False
            if record.get("entry_hash") != self._hash_entry(record):
                return False
            prev = record["entry_hash"]
        return True
