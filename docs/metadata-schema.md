# Metadata schema

FrameGuard keeps a strict split between what stays **off-chain** (the full
manifest) and what gets **anchored** (a tiny record). This is the same on-chain /
off-chain decision NISHAAN makes, applied to video.

## 1. The manifest (off-chain, full record)

Written to `backend/data/manifests/<video_id>.json` at registration. It holds
everything needed to later localize a tampered frame.

```jsonc
{
  "video_id": "demo_clip",
  "created_at": "2026-10-29T03:54:52Z",
  "metadata": {                      // the source file itself
    "filename": "original.mkv",
    "file_size": 92795,
    "file_sha256": "1724ca3b...",    // whole-file hash (for reference, not the anchor)
    "container": "matroska,webm",
    "codec": "ffv1",
    "pixel_format": "bgr0",
    "width": 96,
    "height": 96,
    "native_fps": 30.0,
    "duration_seconds": 2.0,
    "native_frame_count": null,      // null when the container does not report it
    "creation_time": null            // from container tags when present
  },
  "extraction": {                    // how frames were sampled, so it is reproducible
    "target_fps": 15,
    "frame_backend": "ffmpeg",
    "pixel_format": "rgb24",
    "resized": false,
    "note": "Frames sampled at target_fps via the fps filter; raw rgb24 pixels are hashed."
  },
  "frame_count": 30,
  "merkle_root": "1e9a6a08...",
  "metadata_hash": "34d79ed1...",    // binds metadata + extraction + frame_count + root
  "frames": [                        // one entry per sampled frame, in order
    { "index": 0, "timestamp_ms": 0,   "sha256": "..." },
    { "index": 1, "timestamp_ms": 66,  "sha256": "..." }
    // ...
  ]
}
```

## 2. The anchor (on-chain / ledger, minimal record)

Only these fields are written to the blockchain (or the local hash-chained
ledger). The size is constant no matter how long the video is.

| Field           | Type        | Why it is anchored                                        |
|-----------------|-------------|-----------------------------------------------------------|
| `video_id`      | string      | Lookup key.                                               |
| `merkle_root`   | bytes32     | The single fingerprint of all frames.                     |
| `frame_count`   | uint256     | Fixes the tree shape; detects frame insertion/deletion.   |
| `target_fps`    | uint256     | So verification re-samples at the same rate.              |
| `metadata_hash` | bytes32     | Makes the off-chain manifest tamper-evident.              |
| `registrant`    | address     | Who anchored it.                                          |
| `registered_at` | timestamp   | When.                                                     |

### `metadata_hash`

```
metadata_hash = SHA-256( canonical_json({
    metadata, extraction, frame_count, merkle_root
}) )
```

`canonical_json` sorts keys and strips whitespace, so the hash is stable. At
verification time the manifest is re-hashed and compared against the anchored
`metadata_hash`; if someone edits the manifest (say, changes the codec or the
fps), the hashes diverge and the manifest is flagged as altered.

## Why frame-level, not file-level

A whole-file hash (`file_sha256`) only answers "changed / unchanged". The Merkle
tree over per-frame hashes answers **which frames** changed, because every leaf
is one frame and the tree preserves order. That is the whole point of FrameGuard.
