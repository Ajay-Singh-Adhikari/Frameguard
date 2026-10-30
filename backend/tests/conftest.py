import shutil
import subprocess

import pytest

from frameguard.config import Config

FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")


def _make_video(path, pattern="testsrc", size="64x64", rate=30, duration=1):
    """Create a short, lossless (ffv1) synthetic clip. ffv1 is a native ffmpeg
    encoder, so no external codec is required and decoding is exact."""
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"{pattern}=size={size}:rate={rate}:duration={duration}",
            "-c:v", "ffv1", str(path),
        ],
        check=True,
    )
    return str(path)


@pytest.fixture
def config(tmp_path):
    return Config(data_dir=tmp_path / "data", allowed_fps={15, 30}, default_fps=30)


@pytest.fixture
def video_a(tmp_path):
    return _make_video(tmp_path / "a.mkv", pattern="testsrc")


@pytest.fixture
def video_b(tmp_path):
    # Same dimensions/fps/length, different content -> a different Merkle root.
    return _make_video(tmp_path / "b.mkv", pattern="testsrc2")
