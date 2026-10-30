"""The register and verify workflows that tie every module together.

Register:  video -> frames -> per-frame SHA-256 -> Merkle root -> write off-chain
           manifest + anchor the root and minimal metadata.
Verify:    received video -> rebuild root -> compare with the anchored root ->
           if it differs, localize exactly which frame indices changed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union

from .ai import aggregate, build_detector
from .config import Config
from .frames import extract_frames
from .hashing import sha256_bytes
from .merkle import merkle_proof, merkle_root, verify_proof
from .metadata import (
    ExtractionParams,
    FrameRecord,
    Manifest,
    compute_metadata_hash,
    probe_video,
)
from .registry import Registry, build_registry
from .storage import Storage, build_storage
from .util import FrameGuardError, utc_now_iso

# The hybrid trust score fuses the cryptographic term with the AI term, weighted
# by config.crypto_weight (0.6 by default, per the synopsis). When the AI backend
# is "none", the hybrid score equals the cryptographic score.


def _default_video_id(file_sha256: str, target_fps: int) -> str:
    return f"vid_{file_sha256[:12]}_{target_fps}fps"


def _manifest_path(config: Config, video_id: str) -> Path:
    return config.manifest_dir / f"{video_id}.json"


def _process_frames(path, target_fps, meta, config, detector=None):
    """Extract frames once, hashing each and (optionally) scoring it with the AI
    detector. Returns ``(frame_records, ai_frame_scores)``."""
    records: List[FrameRecord] = []
    ai_scores: List[float] = []
    for frame in extract_frames(
        path, target_fps, meta,
        backend=config.frame_backend,
        ffmpeg_bin=config.ffmpeg_bin,
        ffprobe_bin=config.ffprobe_bin,
    ):
        records.append(
            FrameRecord(index=frame.index, timestamp_ms=frame.timestamp_ms, sha256=sha256_bytes(frame.data))
        )
        if detector is not None:
            ai_scores.append(detector.score_frame(frame.data, meta.width, meta.height))
    if not records:
        raise FrameGuardError("No frames were extracted from the video")
    return records, ai_scores


def register_video(
    path: Union[str, Path],
    *,
    target_fps: int,
    config: Config,
    registry: Optional[Registry] = None,
    storage: Optional[Storage] = None,
    video_id: Optional[str] = None,
) -> dict:
    config.ensure_dirs()
    if target_fps not in config.allowed_fps:
        raise FrameGuardError(f"target_fps {target_fps} not allowed; choose from {sorted(config.allowed_fps)}")
    registry = registry or build_registry(config)
    storage = storage or build_storage(config)

    meta = probe_video(path, ffprobe_bin=config.ffprobe_bin)
    video_id = video_id or _default_video_id(meta.file_sha256, target_fps)

    frames, _ = _process_frames(path, target_fps, meta, config)  # AI runs at verify, not register
    leaves = [f.sha256 for f in frames]
    root = merkle_root(leaves)

    extraction = ExtractionParams(target_fps=target_fps, frame_backend=config.frame_backend)
    metadata_hash = compute_metadata_hash(meta, extraction, len(frames), root)

    manifest = Manifest(
        video_id=video_id,
        created_at=utc_now_iso(),
        metadata=meta,
        extraction=extraction,
        frame_count=len(frames),
        merkle_root=root,
        metadata_hash=metadata_hash,
        frames=frames,
    )

    manifest_path = _manifest_path(config, video_id)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(mode="json"), f, indent=2)

    anchor = {
        "video_id": video_id,
        "merkle_root": root,
        "frame_count": len(frames),
        "target_fps": target_fps,
        "metadata_hash": metadata_hash,
        "registrant": "local",
        "registered_at": utc_now_iso(),
    }

    # Off-chain IPFS storage (optional): pin the video + manifest, record the CIDs.
    ipfs_info = None
    if storage is not None:
        video_obj = storage.add_file(path, name=meta.filename)
        manifest_obj = storage.add_file(manifest_path, name=f"{video_id}.manifest.json")
        anchor["video_cid"] = video_obj["cid"]
        anchor["manifest_cid"] = manifest_obj["cid"]
        ipfs_info = {"backend": storage.name, "video": video_obj, "manifest": manifest_obj}

    anchor_record = registry.register(anchor)  # fails if this video_id is already anchored

    return {
        "video_id": video_id,
        "merkle_root": root,
        "frame_count": len(frames),
        "target_fps": target_fps,
        "metadata_hash": metadata_hash,
        "manifest_path": str(manifest_path),
        "anchor": anchor_record,
        "ipfs": ipfs_info,
        "source": meta.model_dump(mode="json"),
    }


def _load_manifest(config: Config, video_id: str) -> Manifest:
    path = _manifest_path(config, video_id)
    if not path.exists():
        raise FrameGuardError(f"No manifest on file for '{video_id}' (expected {path})")
    with open(path, "r", encoding="utf-8") as f:
        return Manifest.model_validate(json.load(f))


def load_manifest(config: Config, video_id: str) -> Manifest:
    """Public accessor for a stored manifest (used by the PDF report)."""
    return _load_manifest(config, video_id)


def verify_video(
    path: Union[str, Path],
    *,
    video_id: str,
    config: Config,
    registry: Optional[Registry] = None,
) -> dict:
    registry = registry or build_registry(config)

    anchor = registry.get(video_id)
    if anchor is None:
        raise FrameGuardError(f"'{video_id}' is not registered")

    manifest = _load_manifest(config, video_id)
    notes: List[str] = []

    # 1) The off-chain manifest must still match what was anchored on-chain.
    recomputed_meta_hash = compute_metadata_hash(
        manifest.metadata, manifest.extraction, manifest.frame_count, manifest.merkle_root
    )
    manifest_intact = (
        recomputed_meta_hash == manifest.metadata_hash
        and manifest.metadata_hash == anchor["metadata_hash"]
        and manifest.merkle_root == anchor["merkle_root"]
    )
    if not manifest_intact:
        notes.append("Off-chain manifest does not match the anchored record; it may have been altered.")

    # 2) Recompute the Merkle root from the received copy (scoring frames too if AI is on).
    target_fps = int(anchor["target_fps"])
    meta = probe_video(path, ffprobe_bin=config.ffprobe_bin)
    detector = build_detector(config)
    received, ai_scores = _process_frames(path, target_fps, meta, config, detector)
    received_leaves = [f.sha256 for f in received]
    recomputed_root = merkle_root(received_leaves)
    root_match = recomputed_root == anchor["merkle_root"]

    # 3) Localize differing frames against the original leaves in the manifest.
    original_leaves = manifest.leaf_hashes()
    overlap = min(len(original_leaves), len(received_leaves))
    tampered = [i for i in range(overlap) if original_leaves[i] != received_leaves[i]]

    frame_count_match = len(original_leaves) == len(received_leaves)
    if not frame_count_match:
        notes.append(
            f"Frame count changed: anchored {len(original_leaves)}, received "
            f"{len(received_leaves)} (frames inserted, deleted, or re-timed)."
        )

    # Sanity check: proving one still-matching frame against the anchored root.
    if root_match and original_leaves:
        proof = merkle_proof(original_leaves, 0)
        if not verify_proof(original_leaves[0], proof, anchor["merkle_root"]):
            notes.append("Internal proof check failed unexpectedly.")

    intact_frames = overlap - len(tampered)
    total = len(original_leaves) or 1
    crypto_score = 100 if root_match else round(100 * max(intact_frames, 0) / total)

    # 4) AI content-manipulation layer + hybrid fusion.
    ai_backend = detector.name if detector is not None else "none"
    ai_manipulation_score: Optional[int] = None
    ai_suspicious_frames: List[int] = []
    crypto_weight = config.crypto_weight
    hybrid_score = crypto_score
    if detector is not None:
        summary = aggregate(ai_scores)
        ai_manipulation_score = summary["manipulation_score"]
        ai_suspicious_frames = summary["suspicious_frames"]
        ai_authenticity = 100 - ai_manipulation_score
        hybrid_score = round(crypto_weight * crypto_score + (1 - crypto_weight) * ai_authenticity)
        if ai_backend == "baseline-heuristic":
            notes.append("AI score is from the baseline-heuristic placeholder, not a trained model.")

    try:
        registry.log_verification(video_id, root_match)
    except Exception:  # logging the verification is best-effort
        notes.append("Could not record verification in the registry log.")

    return {
        "video_id": video_id,
        "target_fps": target_fps,
        "integrity": "INTACT" if root_match else "TAMPERED",
        "root_match": root_match,
        "anchored_root": anchor["merkle_root"],
        "recomputed_root": recomputed_root,
        "manifest_intact": manifest_intact,
        "original_frame_count": len(original_leaves),
        "received_frame_count": len(received_leaves),
        "frame_count_match": frame_count_match,
        "tampered_frames": tampered,
        "intact_frame_count": max(intact_frames, 0),
        "crypto_integrity_score": crypto_score,
        "ai_manipulation_score": ai_manipulation_score,  # None when the AI backend is "none"
        "ai_backend": ai_backend,
        "ai_suspicious_frames": ai_suspicious_frames,
        "hybrid_trust_score": hybrid_score,
        "crypto_weight": crypto_weight,
        "notes": notes,
        "checked_at": utc_now_iso(),
    }
