import shutil
from dataclasses import replace

import pytest

from frameguard.pipeline import register_video, verify_video
from frameguard.registry import build_registry
from frameguard.util import FrameGuardError

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@needs_ffmpeg
def test_register_then_verify_is_intact(config, video_a):
    reg = register_video(video_a, target_fps=15, config=config)
    assert reg["frame_count"] > 0
    assert len(reg["merkle_root"]) == 64

    report = verify_video(video_a, video_id=reg["video_id"], config=config)
    assert report["integrity"] == "INTACT"
    assert report["root_match"] is True
    assert report["tampered_frames"] == []
    assert report["manifest_intact"] is True
    assert report["hybrid_trust_score"] == 100


@needs_ffmpeg
def test_verify_localizes_tampering(config, video_a, video_b):
    reg = register_video(video_a, target_fps=15, config=config)
    report = verify_video(video_b, video_id=reg["video_id"], config=config)
    assert report["integrity"] == "TAMPERED"
    assert report["root_match"] is False
    assert len(report["tampered_frames"]) > 0
    assert report["hybrid_trust_score"] < 100


@needs_ffmpeg
def test_same_video_cannot_be_registered_twice(config, video_a):
    register_video(video_a, target_fps=15, config=config)
    with pytest.raises(FrameGuardError):
        register_video(video_a, target_fps=15, config=config)


@needs_ffmpeg
def test_local_ledger_hash_chain_stays_intact(config, video_a):
    register_video(video_a, target_fps=15, config=config)
    assert build_registry(config).verify_chain() is True


@needs_ffmpeg
def test_verify_fuses_ai_when_enabled(config, video_a):
    reg = register_video(video_a, target_fps=15, config=config)
    ai_config = replace(config, ai_backend="heuristic")
    report = verify_video(video_a, video_id=reg["video_id"], config=ai_config)
    assert report["ai_backend"] == "baseline-heuristic"
    assert report["ai_manipulation_score"] is not None
    assert 0 <= report["ai_manipulation_score"] <= 100
    assert 0 <= report["hybrid_trust_score"] <= 100


@needs_ffmpeg
def test_verify_ai_defaults_to_none(config, video_a):
    reg = register_video(video_a, target_fps=15, config=config)
    report = verify_video(video_a, video_id=reg["video_id"], config=config)
    assert report["ai_backend"] == "none"
    assert report["ai_manipulation_score"] is None
    assert report["hybrid_trust_score"] == report["crypto_integrity_score"]


class _FakeStorage:
    name = "fake"

    def __init__(self):
        self.count = 0

    def add_file(self, path, name=None):
        self.count += 1
        cid = f"cid-{self.count}"
        return {"cid": cid, "size": 1, "backend": self.name, "gateway_url": f"https://gw/{cid}"}

    def add_bytes(self, data, name):
        return self.add_file(name, name)


@needs_ffmpeg
def test_register_with_storage_records_cids(config, video_a):
    reg = register_video(video_a, target_fps=15, config=config, storage=_FakeStorage())
    assert reg["ipfs"]["backend"] == "fake"
    assert reg["ipfs"]["video"]["cid"]
    assert reg["ipfs"]["manifest"]["cid"]
    assert reg["anchor"]["video_cid"]
    assert reg["anchor"]["manifest_cid"]


@needs_ffmpeg
def test_register_without_storage_has_no_ipfs(config, video_a):
    reg = register_video(video_a, target_fps=15, config=config)
    assert reg["ipfs"] is None
