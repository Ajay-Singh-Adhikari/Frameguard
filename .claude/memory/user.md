---
name: user
description: Team member collaboration notes and preferences
metadata:
  type: user
---

# FrameGuard Team Collaboration

## Development Preferences (from project analysis)

### Code Style
- Python: Clean, functional style with dataclasses
- TypeScript: Component-based with Next.js App Router
- SOLID: One responsibility per function/module

### Communication Notes
- Project context is well-documented in CLAUDE.md
- Code is modular and well-tested
- Frontend uses Tailwind CSS for styling
- Backend uses FastAPI with automatic OpenAPI docs

## Current Session Notes

Team is discussing:
- Setting up local development environment
- Understanding project structure from GitHub clone
- Deciding which codebase to work with (original vs cloned)

## Technical Context

### Blockchain Integration Questions
- Sepolia testnet deployed - need to verify contract address
- Infura/Alchemy RPC URL required for chain backend
- Private key for deploying must have Sepolia ETH (get from faucet)

### AI Model Questions
- EfficientNet-B4 weights file needed at `backend/frameguard_ai.pt` or via `FRAMEGUARD_AI_WEIGHTS` env var
- Model can be trained via Google Colab using provided train.py

### IPFS Storage Questions
- Pinata JWT required for pinning files
- Can use local Kubo node as alternative

## Next Actions (Team Decisions Needed)
1. Which codebase to use: original `frameguard` or GitHub clone `Frameguard`?
2. Do we need Ethereum testnet deployment or use local ledger?
3. Should we run the full system locally or just review code?