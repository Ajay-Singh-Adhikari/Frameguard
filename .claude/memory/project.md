---
name: project-overview
description: Core project information for FrameGuard video tamper detection system
metadata:
  type: project
---

# FrameGuard Project Context

**Purpose:** B.Tech final-year major project - blockchain-anchored frame-level video tamper detection

**Core Innovation:** Using Merkle trees to localize video tampering to specific frames, combined with AI detection and a hybrid trust score (0-100).

## What's Already Built

| Component | Status | Location |
|-----------|--------|----------|
| Frame extraction (OpenCV) | ✅ Complete | backend/frameguard/frames.py |
| Merkle tree + proofs | ✅ Complete | backend/frameguard/merkle.py |
| Blockchain anchoring | ✅ Implemented | backend/frameguard/chain.py, contracts/VideoRegistry.sol |
| AI detection stub | ✅ Complete | backend/frameguard/ai.py |
| Verification engine | ✅ Complete | backend/frameguard/pipeline.py |
| Hybrid trust score | ✅ Complete | backend/frameguard/pipeline.py |
| FastAPI backend | ✅ Complete | backend/frameguard/api.py |
| Next.js frontend | ✅ Complete | frontend/src/ |
| Smart contract | ✅ Complete | contracts/contracts/VideoRegistry.sol |
| Test suite | ✅ Complete | backend/tests/ |

## Architecture Decision: Default Mode

The system works **without blockchain or AI** using defaults:
- `anchor_backend=local` - Hash-chained JSON ledger
- `ai_backend=none` - Crypto-only scoring
- `storage_backend=none` - Local file storage

To enable Ethereum: `anchor_backend=chain` + set `.env` with RPC URL/private key

## Key Files to Modify

- `backend/frameguard/config.py` - Configuration options
- `backend/frameguard/pipeline.py` - Core workflows
- `backend/frameguard/merkle.py` - Merkle tree implementation
- `frontend/src/` - Dashboard components
- `contracts/contracts/VideoRegistry.sol` - Smart contract

## Quick Start Commands

```bash
cd backend && source venv/bin/activate && python -m frameguard serve --port 8000
cd frontend && npm run dev
```

## API Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/health` | GET | Check backend status |
| `/register` | POST | Upload + register video |
| `/verify` | POST | Verify a video copy |
| `/videos/{id}` | GET | Get registered video |
| `/report` | POST | Generate PDF report |

## Working Together

- Branch naming: `feature/<name>`, `bugfix/<name>`, `hotfix/<name>`
- PR process: Open PR when implementation is complete, request review from team
- Testing: Run `pytest backend/tests/` before pushing
- Documentation: Update MEMORY.md for significant decisions
- Smart contract: Deploy via Hardhat, verify address is in `.env`