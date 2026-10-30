# Architecture

FrameGuard applies the NISHAAN ("Evidence Chain") anchoring idea to video, at
**frame level**. Instead of storing one fingerprint for a file, it stores one
Merkle root that covers every frame, so a later check can say *which* frames
were altered.

## The two workflows

### Register

```
video ──▶ ffprobe (metadata)
      ──▶ ffmpeg: sample frames at target_fps (15 or 30), raw rgb24
          └─ for each frame: SHA-256(frame bytes)        ◀── the "loop per frame"
      ──▶ Merkle tree over the frame hashes ──▶ merkle_root
      ──▶ manifest.json  (off-chain: all frame hashes + metadata)
      ──▶ anchor         (on-chain/ledger: root + frame_count + fps + metadata_hash)
```

### Verify

```
received video ──▶ re-sample frames at the anchored fps ──▶ SHA-256 each ──▶ rebuild root
   compare rebuilt root with the anchored root
      ├─ equal      ▶ INTACT
      └─ different   ▶ TAMPERED
                      └─ compare received frame hashes vs the manifest, index by index
                         ▶ exact tampered frame numbers  (+ note if frames were added/removed)
```

## Modules (`backend/frameguard/`)

| Module         | Responsibility                                                        |
|----------------|-----------------------------------------------------------------------|
| `frames.py`    | Extract frames at a target fps (ffmpeg default; OpenCV optional).      |
| `hashing.py`   | SHA-256 of frame bytes and whole files.                               |
| `merkle.py`    | Build the tree, the root, inclusion proofs, and proof verification.    |
| `metadata.py`  | ffprobe metadata + the manifest / anchor data models + `metadata_hash`.|
| `ai.py`        | AI content-manipulation detectors (none / baseline / EfficientNet-B4). |
| `storage.py`   | Off-chain IPFS storage for the video + manifest (Pinata / local node).  |
| `report.py`    | One-page PDF verification report (fpdf2).                              |
| `ledger.py`    | Local append-only, **hash-chained** anchor (the zero-setup default).   |
| `chain.py`     | On-chain anchor via the `VideoRegistry` contract (optional, web3).     |
| `registry.py`  | Chooses the anchor backend from config.                               |
| `pipeline.py`  | The `register_video` / `verify_video` orchestration + trust score.    |
| `api.py`       | FastAPI endpoints.                                                    |
| `__main__.py`  | CLI (`python -m frameguard ...`).                                     |

## On-chain / off-chain split

Exactly as in the synopsis: only the Merkle root and minimal metadata are
anchored; the video, the per-frame hashes and the full tree stay off-chain.
Registration is one write regardless of length, so a 10-second and a 10-minute
clip cost the same to anchor.

Two anchor backends implement the same interface:

* **Local ledger** (default) — a JSON file where each record links to the hash of
  the previous one, so past entries cannot be edited without detection. No setup.
* **Chain** — the Solidity `VideoRegistry` on a local Hardhat node or Sepolia.

## The Merkle tree

* Leaves = per-frame SHA-256 digests, in frame order.
* Internal node = `SHA-256(0x01 || left || right)` — the `0x01` prefix separates
  internal nodes from leaves (second-preimage hardening).
* Odd level → duplicate the last node. `frame_count` is anchored, so the tree
  shape is fixed and the duplication is unambiguous.

Ordering is deliberate: leaf *i* is frame *i*, which is what makes
frame-level localization possible.

## Trust score and the AI layer

The verifier returns a `hybrid_trust_score` (0–100):

```
hybrid = crypto_weight * crypto_score + (1 - crypto_weight) * ai_authenticity
```

where `crypto_score` is the cryptographic integrity (100 if the root matches,
else the proportion of intact frames), `ai_authenticity = 100 - ai_manipulation`,
and `crypto_weight` is 0.6 by default (the synopsis's 0.6/0.4 split).

The AI term is pluggable (`ai.py`, selected by `FRAMEGUARD_AI_BACKEND`):

* `none` (default) — `ai_manipulation_score` stays `null` and the hybrid score
  equals the cryptographic score, so it is never inflated by a component that is
  not really there.
* `heuristic` — a dependency-free, deterministic **placeholder** so the fusion
  and plumbing can be run and tested before the model exists. It is labelled as a
  placeholder everywhere it surfaces; it is not a real detector.
* `efficientnet` — the real EfficientNet-B4 classifier (lazy torch import +
  trained weights). This is the interface the FaceForensics++-trained model plugs
  into. The AI layer runs only at verify time (it targets fabricated content,
  which hashing structurally cannot catch).

## Known limits (next-phase work, per the synopsis)

* **Re-encoding** changes pixel values without malicious intent and currently
  reads as tampering. A perceptual/robust-hash step is future work.
* **Insertion / deletion / reordering** is detected (frame count + index diff)
  but not yet aligned with an LCS-style diff to pinpoint shifts.
* **AI content detection** — the interface, the hybrid fusion, and a baseline
  placeholder are in place; training the EfficientNet-B4 model (FaceForensics++)
  and loading its weights is the remaining next-phase work.
* **IPFS storage** pins the video + manifest and records their CIDs (Pinata or a
  local node); recording the CID on the Solidity contract (not just the local
  ledger) is a small follow-up.
