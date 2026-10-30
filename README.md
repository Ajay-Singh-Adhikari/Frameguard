# FrameGuard

**Frame-level video tamper detection, anchored on a Merkle root.**

FrameGuard is the video counterpart to NISHAAN ("Evidence Chain"). Where a
whole-file hash can only tell you a video *changed*, FrameGuard tells you
**which frames** changed. Every frame is hashed with SHA-256, the frame hashes
are combined into a single Merkle tree, and only that 32-byte root plus a little
metadata is anchored. A 10-second clip and a 10-minute clip cost the same to
register, because only the root is stored — not the frames.

This repository is the **core pipeline MVP**: upload/point at a video → break it
into frames at 30 or 15 fps → SHA-256 each frame → build the Merkle tree →
anchor the root + metadata → verify a received copy and localize the exact
tampered frame numbers.

```
video ─▶ frames (30/15 fps) ─▶ SHA-256 per frame ─▶ Merkle root ─▶ anchor
copy  ─▶ rebuild root ─▶ compare ─▶ INTACT, or TAMPERED + exact frame numbers
```

## Quickstart (zero setup)

Needs Python 3.11+ and `ffmpeg`/`ffprobe` on the PATH (`brew install ffmpeg`).
In the default mode, anchoring uses a local hash-chained ledger file — no
blockchain required.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Register a video (anchor its Merkle root), sampling at 15 fps
python -m frameguard register path/to/video.mp4 --fps 15 --video-id my_clip

# Verify a received copy against the anchor
python -m frameguard verify path/to/received.mp4 --video-id my_clip

# Confirm the local ledger's hash chain is intact
python -m frameguard ledger-check

# Or run the HTTP API
python -m frameguard serve --port 8000   # GET /health, POST /register, POST /verify
```

A tampered copy reports exactly which frames differ:

```jsonc
{
  "integrity": "TAMPERED",
  "root_match": false,
  "tampered_frames": [15, 16, 17],
  "intact_frame_count": 27,
  "hybrid_trust_score": 90
}
```

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

The suite covers the SHA-256 vectors, the Merkle tree + proofs, metadata
hashing, and a full ffmpeg round trip (register → verify intact → tamper →
localize). The pipeline tests skip automatically if ffmpeg is absent.

## Dashboard (web UI)

A Next.js dashboard to register a video, verify a copy, and see a **frame-level
timeline** that marks the exact frames that differ. Start the API first, then:

```bash
cd frontend
npm install
cp .env.example .env.local        # points at http://127.0.0.1:8000 by default
npm run dev                        # open http://localhost:3000
```

The page reads `/health`, posts to `/register` and `/verify`, and renders the
verdict (INTACT / TAMPERED), the trust score, the two Merkle roots, and the
timeline. CORS for `localhost:3000` is already enabled on the backend.

## AI content detection (optional)

The second evidence layer scores frames for content-level manipulation (a
fabricated clip that hashing can't catch) and fuses into the trust score at
`0.6 crypto / 0.4 AI`. Three backends share one interface:

- `none` (default) — AI score stays `null`; hybrid score = cryptographic score.
- `heuristic` — a dependency-free, deterministic **placeholder** so the fusion is
  runnable now (not a real detector; clearly labelled everywhere it appears).
- `efficientnet` — the real EfficientNet-B4 classifier; needs trained weights and
  `pip install -r backend/requirements-ai.txt` (torch).

```bash
# Try the fusion end to end with the placeholder backend:
python -m frameguard verify copy.mp4 --video-id my_clip --ai heuristic

# Or enable a backend for the server / all runs:
export FRAMEGUARD_AI_BACKEND=efficientnet
export FRAMEGUARD_AI_WEIGHTS=/path/to/efficientnet_b4.pt
```

Training the FaceForensics++ model and dropping the weights behind the
`efficientnet` backend is the remaining next-phase work.

## IPFS storage (optional)

At registration the video and the manifest can be content-addressed on IPFS and
their CIDs recorded alongside the anchor (the off-chain half of the split). Two
backends, `none` by default:

- `pinata` — pin via the Pinata service; needs `FRAMEGUARD_PINATA_JWT`.
- `ipfs` — a local Kubo node's HTTP API (`ipfs daemon`), `FRAMEGUARD_IPFS_API`.

```bash
# Pin with Pinata for one run:
export FRAMEGUARD_PINATA_JWT=...     # or FRAMEGUARD_STORAGE_BACKEND=pinata
python -m frameguard register video.mp4 --fps 15 --storage pinata
# -> result.ipfs.video.cid / .manifest.cid + gateway URLs; CIDs also on the anchor
```

## Anchoring on a real chain (optional)

The default local ledger is swappable for the Solidity `VideoRegistry` contract.

```bash
cd contracts
npm install
npx hardhat test                 # contract smoke tests
npx hardhat node                 # local chain in another terminal
npm run deploy:local             # or deploy:sepolia with contracts/.env
```

Then point the backend at it:

```bash
export FRAMEGUARD_ANCHOR_BACKEND=chain
export FRAMEGUARD_RPC_URL=http://127.0.0.1:8545
export FRAMEGUARD_CONTRACT_ADDRESS=0x...        # from the deploy output
export FRAMEGUARD_PRIVATE_KEY=0x...
pip install -r backend/requirements-chain.txt   # installs web3
```

## Repository layout

```
frameguard/
├── backend/            Python core pipeline + FastAPI + CLI
│   ├── frameguard/     frames, hashing, merkle, metadata, ledger, chain, pipeline, api
│   └── tests/          unit + end-to-end tests
├── frontend/           Next.js dashboard (register, verify, frame-level timeline)
├── contracts/          Hardhat project: VideoRegistry.sol, deploy, smoke tests
└── docs/               architecture.md, metadata-schema.md
```

## How it maps to the synopsis

| Synopsis item                              | Status in this MVP                         |
|--------------------------------------------|--------------------------------------------|
| Frame extraction (OpenCV)                  | ✅ ffmpeg default + optional OpenCV backend |
| Per-frame SHA-256                          | ✅                                          |
| Merkle tree + root + proofs                | ✅                                          |
| Blockchain registration                    | ✅ local hash-chained ledger + Solidity `VideoRegistry` |
| Verification + frame-level localization    | ✅                                          |
| Minimal on-chain / full off-chain split    | ✅ (anchor vs. manifest)                    |
| EfficientNet-B4 content detection          | 🟡 interface scaffolded (torch path + baseline); model training next |
| Hybrid Trust Score (0.6 crypto / 0.4 AI)   | ✅ fusion wired; active when an AI backend is enabled |
| React dashboard with frame-level timeline  | ✅ `frontend/` (Next.js)                     |
| PDF verification report                    | ✅ `/report` endpoint + CLI + dashboard button |
| IPFS storage (video + manifest)            | ✅ Pinata + local IPFS node backends        |

See [`docs/architecture.md`](docs/architecture.md) and
[`docs/metadata-schema.md`](docs/metadata-schema.md) for details.
