"""FastAPI surface for the platform.

Endpoints
---------
GET  /health              liveness + which backends are active
POST /register            upload a video, get back its Merkle root + anchor
POST /verify              upload a copy, get an integrity report + tampered frames
GET  /videos/{video_id}   the anchored record for a video
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import Config
from .pipeline import load_manifest, register_video, verify_video
from .registry import build_registry
from .report import build_report_pdf
from .util import FrameGuardError

config = Config.from_env()
app = FastAPI(title="FrameGuard", version=__version__,
              description="Frame-level video tamper detection anchored on a Merkle root.")


def _cors_origins() -> list[str]:
    raw = os.getenv("FRAMEGUARD_CORS_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


# The dashboard (Next.js) calls these endpoints from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload(file: UploadFile, dest: Path, max_bytes: int) -> None:
    size = 0
    with open(dest, "wb") as out:
        while True:
            chunk = file.file.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Uploaded video exceeds the size limit")
            out.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty upload")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "frame_backend": config.frame_backend,
        "anchor_backend": config.anchor_backend,
        "ai_backend": config.ai_backend,
        "storage_backend": config.storage_backend,
        "allowed_fps": sorted(config.allowed_fps),
    }


@app.post("/register")
def register(file: UploadFile = File(...), target_fps: int = Form(30), video_id: str | None = Form(None)) -> dict:
    if target_fps not in config.allowed_fps:
        raise HTTPException(status_code=422, detail=f"target_fps must be one of {sorted(config.allowed_fps)}")
    config.ensure_dirs()
    tmp = config.upload_dir / f"reg_{uuid.uuid4().hex}_{Path(file.filename or 'video').name}"
    _save_upload(file, tmp, config.max_upload_bytes)
    try:
        return register_video(tmp, target_fps=target_fps, config=config, video_id=video_id or None)
    except FrameGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp.unlink(missing_ok=True)


@app.post("/verify")
def verify(file: UploadFile = File(...), video_id: str = Form(...)) -> dict:
    config.ensure_dirs()
    tmp = config.upload_dir / f"ver_{uuid.uuid4().hex}_{Path(file.filename or 'video').name}"
    _save_upload(file, tmp, config.max_upload_bytes)
    try:
        return verify_video(tmp, video_id=video_id, config=config)
    except FrameGuardError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        tmp.unlink(missing_ok=True)


@app.get("/videos/{video_id}")
def get_video(video_id: str) -> JSONResponse:
    anchor = build_registry(config).get(video_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail=f"'{video_id}' is not registered")
    return JSONResponse(anchor)


@app.post("/report")
def report(payload: dict = Body(...)) -> Response:
    """Render a PDF verification report from a verify result (as returned by /verify)."""
    video_id = payload.get("video_id")
    if not video_id:
        raise HTTPException(status_code=422, detail="Report payload is missing 'video_id'")

    anchor = build_registry(config).get(video_id)  # authoritative registration fields
    try:
        manifest = load_manifest(config, video_id)
    except FrameGuardError:
        manifest = None

    pdf = build_report_pdf(payload, anchor=anchor, manifest=manifest)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="frameguard-{video_id}.pdf"'},
    )
