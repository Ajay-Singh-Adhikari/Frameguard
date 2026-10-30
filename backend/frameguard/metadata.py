"""Video metadata probing and the data models for manifests and anchors.

The split mirrors the NISHAAN design decision:

* The **manifest** is the full off-chain record: every per-frame hash, the whole
  Merkle tree's root, and all metadata. It stays on disk and is never trusted on
  its own.
* The **anchor** is the minimal on-chain (or hash-chained ledger) record: the
  video id, the Merkle root, the frame count, the sampling fps, and a hash that
  binds the manifest's metadata. One small record regardless of video length.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from .hashing import sha256_file
from .util import FrameGuardError, canonical_json, sha256_hex


class VideoMetadata(BaseModel):
    """Everything we know about the source file itself."""

    filename: str
    file_size: int
    file_sha256: str
    container: Optional[str] = None
    codec: Optional[str] = None
    pixel_format: Optional[str] = None
    width: int
    height: int
    native_fps: float
    duration_seconds: Optional[float] = None
    native_frame_count: Optional[int] = None
    creation_time: Optional[str] = None


class ExtractionParams(BaseModel):
    """How the frames were sampled from the source, so it can be reproduced."""

    target_fps: int
    frame_backend: str
    pixel_format: str = "rgb24"
    resized: bool = False
    note: str = "Frames sampled at target_fps via the fps filter; raw rgb24 pixels are hashed."


class FrameRecord(BaseModel):
    index: int
    timestamp_ms: int
    sha256: str


class Manifest(BaseModel):
    """The full off-chain record of a registered video."""

    video_id: str
    created_at: str
    metadata: VideoMetadata
    extraction: ExtractionParams
    frame_count: int
    merkle_root: str
    metadata_hash: str
    frames: List[FrameRecord]

    def leaf_hashes(self) -> List[str]:
        return [f.sha256 for f in self.frames]


def compute_metadata_hash(
    metadata: VideoMetadata, extraction: ExtractionParams, frame_count: int, merkle_root: str
) -> str:
    """Hash that binds the manifest's metadata to its root.

    Anchored next to the root so that the off-chain manifest cannot be edited
    (e.g. swapping the codec or fps) without the anchor noticing.
    """
    core = {
        "metadata": metadata.model_dump(mode="json"),
        "extraction": extraction.model_dump(mode="json"),
        "frame_count": frame_count,
        "merkle_root": merkle_root,
    }
    return sha256_hex(canonical_json(core))


def _parse_fraction(value: Optional[str]) -> float:
    if not value or "/" not in value:
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
    num, den = value.split("/", 1)
    try:
        n, d = float(num), float(den)
        return n / d if d else 0.0
    except ValueError:
        return 0.0


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def probe_video(path: Union[str, Path], ffprobe_bin: str = "ffprobe") -> VideoMetadata:
    """Read container/stream metadata with ffprobe and the file hash locally."""
    path = Path(path)
    if not path.exists():
        raise FrameGuardError(f"Video file not found: {path}")

    cmd = [
        ffprobe_bin, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError as exc:
        raise FrameGuardError(f"ffprobe not found ('{ffprobe_bin}'); install ffmpeg") from exc
    if out.returncode != 0:
        raise FrameGuardError(f"ffprobe failed: {out.stderr.strip()}")

    info = json.loads(out.stdout)
    video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise FrameGuardError("No video stream found in file")

    fmt = info.get("format", {})
    fps = _parse_fraction(video_stream.get("avg_frame_rate")) or _parse_fraction(
        video_stream.get("r_frame_rate")
    )
    nb_frames = video_stream.get("nb_frames")
    tags = fmt.get("tags", {}) or {}

    return VideoMetadata(
        filename=path.name,
        file_size=path.stat().st_size,
        file_sha256=sha256_file(path),
        container=fmt.get("format_name"),
        codec=video_stream.get("codec_name"),
        pixel_format=video_stream.get("pix_fmt"),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        native_fps=round(fps, 6),
        duration_seconds=_to_float(video_stream.get("duration")) or _to_float(fmt.get("duration")),
        native_frame_count=int(nb_frames) if nb_frames and str(nb_frames).isdigit() else None,
        creation_time=tags.get("creation_time"),
    )
