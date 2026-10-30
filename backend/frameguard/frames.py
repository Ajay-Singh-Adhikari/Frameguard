"""Frame extraction.

The default backend shells out to ffmpeg and reads raw ``rgb24`` pixels, so the
bytes we hash are the decoded image, independent of any re-encoding container
quirks. An OpenCV backend is provided too, because the project synopsis names
OpenCV; it is selectable via ``FRAMEGUARD_FRAME_BACKEND=opencv``.

Frames are sampled at ``target_fps`` using ffmpeg's ``fps`` filter, which picks
one frame per ``1/target_fps`` second window. Sampling by time (not by native
frame index) keeps the extraction stable across sources with odd frame rates.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Union

from .metadata import VideoMetadata, probe_video
from .util import FrameGuardError


@dataclass
class Frame:
    index: int
    timestamp_ms: int
    data: bytes  # raw rgb24 pixels for this frame


def _read_exactly(stream, n: int) -> Optional[bytes]:
    """Read exactly ``n`` bytes, or return None at a clean end of stream."""
    buf = bytearray()
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            return None  # EOF (a trailing partial frame is dropped, which should not happen)
        buf.extend(chunk)
    return bytes(buf)


def _extract_ffmpeg(path: Path, target_fps: int, meta: VideoMetadata, ffmpeg_bin: str) -> Iterator[Frame]:
    frame_size = meta.width * meta.height * 3  # rgb24 = 3 bytes/pixel
    cmd = [
        ffmpeg_bin, "-nostdin", "-loglevel", "error", "-i", str(path),
        "-vf", f"fps={target_fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise FrameGuardError(f"ffmpeg not found ('{ffmpeg_bin}'); install ffmpeg") from exc

    index = 0
    try:
        while True:
            buf = _read_exactly(proc.stdout, frame_size)
            if buf is None:
                break
            yield Frame(index=index, timestamp_ms=round(index * 1000 / target_fps), data=buf)
            index += 1
    finally:
        if proc.stdout:
            proc.stdout.close()
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        proc.wait()
        if proc.returncode not in (0, None) and index == 0:
            raise FrameGuardError(f"ffmpeg frame extraction failed: {stderr.strip()}")


def _extract_opencv(path: Path, target_fps: int, meta: VideoMetadata) -> Iterator[Frame]:
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise FrameGuardError("OpenCV backend requested but 'opencv-python' is not installed") from exc

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FrameGuardError(f"OpenCV could not open video: {path}")
    native = meta.native_fps or float(target_fps)
    step = max(native / target_fps, 1.0)
    try:
        native_idx, out_idx, next_pick = 0, 0, 0.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if native_idx >= round(next_pick):
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yield Frame(index=out_idx, timestamp_ms=round(out_idx * 1000 / target_fps), data=rgb.tobytes())
                out_idx += 1
                next_pick += step
            native_idx += 1
    finally:
        cap.release()


def extract_frames(
    path: Union[str, Path],
    target_fps: int,
    meta: Optional[VideoMetadata] = None,
    *,
    backend: str = "ffmpeg",
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
) -> Iterator[Frame]:
    """Yield frames sampled at ``target_fps``, in order, each with raw pixels."""
    if target_fps <= 0:
        raise FrameGuardError("target_fps must be positive")
    path = Path(path)
    meta = meta or probe_video(path, ffprobe_bin=ffprobe_bin)
    if backend == "opencv":
        yield from _extract_opencv(path, target_fps, meta)
    else:
        yield from _extract_ffmpeg(path, target_fps, meta, ffmpeg_bin)
