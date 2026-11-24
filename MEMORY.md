# FrameGuard Project Memory

This file indexes the Claude Code memory files for the FrameGuard project. All team members should review these before starting work to ensure consistent context.

## Memory Files Index

- [Project Overview](.claude/memory/project.md) — Core project info, architecture, setup, and key files
- [Team Notes](.claude/memory/user.md) — Collaboration notes and session context
- [References](.claude/memory/reference.md) — External links, documentation, and resources

## Quick Start (For New Team Members)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with default settings (local ledger, no AI)
python -m frameguard serve --port 8000

cd ../frontend
npm install
npm run dev
```

**Access:** Frontend at http://localhost:3000 | API at http://localhost:8000

## Project Overview

**FrameGuard** is a blockchain-anchored frame-level video tamper detection system that uses Merkle trees to verify video integrity and localize tampering to specific frames.

### Core Architecture

| Module | Purpose | Technology |
|--------|---------|------------|
| 1 | Video Ingestion & Frame Extraction | OpenCV |
| 2 | Merkle Tree Hashing | Python hashlib (SHA-256) |
| 3 | Blockchain Registration | Solidity/Hardhat, Ethereum Sepolia |
| 4 | AI Tamper Detection | EfficientNet-B4 (PyTorch) |
| 5 | Verification Engine | hashlib, Web3.py |
| 6 | Hybrid Trust Score | Python (0.6 crypto + 0.4 AI weight) |
| 7 | Dashboard | React + FastAPI |
| 8 | Storage | IPFS (Pinata) or local |

## Current Working State

The project works **without blockchain or AI** using defaults:
- `anchor_backend=local` - Hash-chained JSON ledger
- `ai_backend=none` - Crypto-only scoring  
- `storage_backend=none` - Local file storage

To enable Ethereum: `anchor_backend=chain` + set `.env` with RPC URL/private key

## API Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/health` | GET | Check backend status |
| `/register` | POST | Upload + register video |
| `/verify` | POST | Verify a video copy |
| `/videos/{id}` | GET | Get registered video |
| `/report` | POST | Generate PDF report |

## File Structure

```
frameguard-project/
├── backend/
│   └── frameguard/           # Source code
├── contracts/
│   └── contracts/VideoRegistry.sol
├── frontend/
│   └── src/                  # Next.js app
├── .claude/memory/
│   ├── project.md            # ← Primary reference
│   ├── user.md               # ← Team collaboration
│   └── reference.md          # ← External links
├── MEMORY.md                 # ← This index file
├── README.md
└── CLAUDE.md                 # Detailed technical spec
```

## Quick Testing Commands

```bash
# Test locally (no blockchain)
cd backend && source venv/bin/activate && python -m frameguard register test.mp4 --fps 30

# Run full test suite
cd backend && pytest tests/ -v
```