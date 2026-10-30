from frameguard.ai import HeuristicBaselineDetector, aggregate, build_detector
from frameguard.config import Config


def test_heuristic_is_deterministic_and_bounded():
    det = HeuristicBaselineDetector()
    frame = bytes(range(256)) * 12  # 3072 bytes, 1024 rgb pixels
    s1 = det.score_frame(frame, 32, 32)
    s2 = det.score_frame(frame, 32, 32)
    assert s1 == s2
    assert 0.0 <= s1 <= 1.0


def test_build_detector_none_and_heuristic():
    assert build_detector(Config(ai_backend="none")) is None
    det = build_detector(Config(ai_backend="heuristic"))
    assert det is not None and det.name == "baseline-heuristic"


def test_aggregate_mean_and_suspicious():
    out = aggregate([0.1, 0.9, 0.2, 0.8])
    assert out["manipulation_score"] == round((0.1 + 0.9 + 0.2 + 0.8) / 4 * 100)
    # Suspicious frames are those above the mean.
    assert set(out["suspicious_frames"]) == {1, 3}


def test_aggregate_empty():
    out = aggregate([])
    assert out["manipulation_score"] == 0
    assert out["suspicious_frames"] == []
