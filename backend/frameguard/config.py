"""Runtime configuration, read from environment variables with safe defaults.

The defaults make the platform run with zero setup: frames are extracted with
ffmpeg and anchors are written to a local hash-chained ledger file. Point
``FRAMEGUARD_ANCHOR_BACKEND=chain`` and fill the chain settings to anchor on a
real Ethereum contract instead.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.isdigit() else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


@dataclass
class Config:
    data_dir: Path = _DEFAULT_DATA_DIR
    # Frame sampling rates the platform accepts. The user-facing default is 15 or 30.
    allowed_fps: Set[int] = field(default_factory=lambda: {15, 30})
    default_fps: int = 30
    max_upload_bytes: int = 500 * 1024 * 1024  # 500 MB

    frame_backend: str = "ffmpeg"  # "ffmpeg" (default) or "opencv"
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    anchor_backend: str = "local"  # "local" (hash-chained JSON ledger) or "chain"

    # AI content-manipulation layer (verify time). "none" keeps the score null.
    ai_backend: str = "none"  # "none" | "heuristic" | "efficientnet"
    ai_weights_path: Optional[str] = None  # trained EfficientNet-B4 weights
    ai_device: str = "cpu"
    crypto_weight: float = 0.6  # hybrid score = crypto_weight*crypto + (1-crypto_weight)*ai

    # Off-chain IPFS storage for the video + manifest (register time).
    storage_backend: str = "none"  # "none" | "pinata" | "ipfs"
    pinata_jwt: Optional[str] = None
    ipfs_api_url: str = "http://127.0.0.1:5001"  # local Kubo node HTTP API
    ipfs_gateway: str = "https://ipfs.io/ipfs/"

    # Only needed when anchor_backend == "chain".
    rpc_url: Optional[str] = None
    contract_address: Optional[str] = None
    private_key: Optional[str] = None
    chain_id: Optional[int] = None

    @property
    def manifest_dir(self) -> Path:
        return self.data_dir / "manifests"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def ledger_path(self) -> Path:
        return self.data_dir / "ledger.json"

    def ensure_dirs(self) -> None:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        data_dir = Path(os.getenv("FRAMEGUARD_DATA_DIR", str(_DEFAULT_DATA_DIR)))
        allowed = os.getenv("FRAMEGUARD_ALLOWED_FPS")
        allowed_fps = {int(x) for x in allowed.split(",") if x.strip().isdigit()} if allowed else {15, 30}
        chain_id = os.getenv("FRAMEGUARD_CHAIN_ID")
        return cls(
            data_dir=data_dir,
            allowed_fps=allowed_fps or {15, 30},
            default_fps=_env_int("FRAMEGUARD_DEFAULT_FPS", 30),
            max_upload_bytes=_env_int("FRAMEGUARD_MAX_UPLOAD_BYTES", 500 * 1024 * 1024),
            frame_backend=os.getenv("FRAMEGUARD_FRAME_BACKEND", "ffmpeg"),
            ffmpeg_bin=os.getenv("FRAMEGUARD_FFMPEG_BIN", "ffmpeg"),
            ffprobe_bin=os.getenv("FRAMEGUARD_FFPROBE_BIN", "ffprobe"),
            anchor_backend=os.getenv("FRAMEGUARD_ANCHOR_BACKEND", "local"),
            rpc_url=os.getenv("FRAMEGUARD_RPC_URL"),
            contract_address=os.getenv("FRAMEGUARD_CONTRACT_ADDRESS"),
            private_key=os.getenv("FRAMEGUARD_PRIVATE_KEY"),
            chain_id=int(chain_id) if chain_id and chain_id.isdigit() else None,
            ai_backend=os.getenv("FRAMEGUARD_AI_BACKEND", "none"),
            ai_weights_path=os.getenv("FRAMEGUARD_AI_WEIGHTS"),
            ai_device=os.getenv("FRAMEGUARD_AI_DEVICE", "cpu"),
            crypto_weight=_env_float("FRAMEGUARD_CRYPTO_WEIGHT", 0.6),
        )
