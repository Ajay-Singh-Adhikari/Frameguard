"""Command-line entry point: ``python -m frameguard <command>``.

    python -m frameguard register path/to/video.mp4 --fps 30
    python -m frameguard verify   path/to/copy.mp4  --video-id vid_abc123_30fps
    python -m frameguard ledger-check
    python -m frameguard serve --port 8000
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import Config
from .pipeline import register_video, verify_video
from .registry import build_registry
from .util import FrameGuardError


def _print(obj: dict) -> None:
    print(json.dumps(obj, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="frameguard", description="Frame-level video tamper detection.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register", help="Register a video and anchor its Merkle root")
    p_reg.add_argument("video")
    p_reg.add_argument("--fps", type=int, default=None, help="Sampling fps (default from config: 15 or 30)")
    p_reg.add_argument("--video-id", default=None)
    p_reg.add_argument("--storage", choices=["none", "pinata", "ipfs"], default=None,
                       help="IPFS storage backend (overrides config for this run)")

    p_ver = sub.add_parser("verify", help="Verify a received copy against its anchor")
    p_ver.add_argument("video")
    p_ver.add_argument("--video-id", required=True)
    p_ver.add_argument("--ai", choices=["none", "heuristic", "efficientnet"], default=None,
                       help="AI content-detection backend (overrides config for this run)")

    p_rep = sub.add_parser("report", help="Verify a copy and write a PDF report")
    p_rep.add_argument("video")
    p_rep.add_argument("--video-id", required=True)
    p_rep.add_argument("-o", "--output", default=None, help="Output PDF path")
    p_rep.add_argument("--ai", choices=["none", "heuristic", "efficientnet"], default=None,
                       help="AI content-detection backend (overrides config for this run)")

    sub.add_parser("ledger-check", help="Check the local ledger's hash chain is intact")

    p_serve = sub.add_parser("serve", help="Run the HTTP API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    config = Config.from_env()
    if getattr(args, "ai", None):
        config.ai_backend = args.ai
    if getattr(args, "storage", None):
        config.storage_backend = args.storage

    try:
        if args.command == "register":
            result = register_video(
                args.video, target_fps=args.fps or config.default_fps, config=config, video_id=args.video_id
            )
            _print(result)
        elif args.command == "verify":
            _print(verify_video(args.video, video_id=args.video_id, config=config))
        elif args.command == "report":
            from .pipeline import load_manifest
            from .report import build_report_pdf

            result = verify_video(args.video, video_id=args.video_id, config=config)
            anchor = build_registry(config).get(args.video_id)
            try:
                manifest = load_manifest(config, args.video_id)
            except FrameGuardError:
                manifest = None
            pdf = build_report_pdf(result, anchor=anchor, manifest=manifest)
            out = args.output or f"frameguard-{args.video_id}.pdf"
            with open(out, "wb") as f:
                f.write(pdf)
            _print({"report": out, "integrity": result["integrity"], "trust_score": result["hybrid_trust_score"]})
        elif args.command == "ledger-check":
            registry = build_registry(config)
            ok = registry.verify_chain() if hasattr(registry, "verify_chain") else True
            _print({"ledger": str(config.ledger_path), "chain_intact": ok})
        elif args.command == "serve":
            import uvicorn

            uvicorn.run("frameguard.api:app", host=args.host, port=args.port)
    except FrameGuardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
