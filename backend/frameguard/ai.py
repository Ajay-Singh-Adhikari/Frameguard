"""AI content-manipulation layer.

This is the second evidence layer from the synopsis: a model that scores each
frame for signs of content-level manipulation (a deepfake / fabricated video that
hashing alone cannot catch, because it was never tampered *after* registration).

Three backends share one interface so the pipeline does not care which runs:

* ``none``        — disabled; the AI score stays ``null`` (default).
* ``heuristic``   — a dependency-free, deterministic placeholder. It is NOT a
                    tamper detector; it exists only so the per-frame scoring,
                    aggregation and hybrid-score fusion can be run and tested
                    before the real model is trained.
* ``efficientnet``— the real EfficientNet-B4 classifier (requires torch +
                    trained weights, via requirements-ai.txt). This is the
                    interface to plug the FaceForensics++-trained model into.

A detector returns a per-frame manipulation probability in ``[0, 1]`` (higher =
more likely manipulated).
"""
from __future__ import annotations

from typing import List, Optional, Protocol, Sequence

from .config import Config
from .util import FrameGuardError

# Up to this many of the most-suspicious frames are reported.
TOP_SUSPICIOUS = 5


class FrameDetector(Protocol):
    name: str

    def score_frame(self, rgb: bytes, width: int, height: int) -> float:
        """Return a manipulation probability in [0, 1] for one rgb24 frame."""
        ...


class HeuristicBaselineDetector:
    """Dependency-free stand-in. Deterministic, bounded, and clearly not a model.

    It derives a value from sampled pixel activity so the plumbing produces
    meaningful, repeatable numbers. Replace it with :class:`EfficientNetDetector`
    once the model is trained — the interface is identical.
    """

    name = "baseline-heuristic"

    def score_frame(self, rgb: bytes, width: int, height: int) -> float:
        n = len(rgb)
        if n < 6:
            return 0.0
        # Sample ~1000 pixels spread across the frame (step aligned to rgb triples).
        step = max(3, ((n // 3000) * 3) or 3)
        total = 0
        count = 0
        for i in range(0, n - step, step):
            a, b = rgb[i], rgb[i + step]
            total += a - b if a >= b else b - a
            count += 1
        if count == 0:
            return 0.0
        activity = (total / count) / 255.0  # 0..1 mean local variation
        # Natural footage sits in a mid band; unusually flat or noisy is nudged up.
        return max(0.0, min(1.0, abs(activity - 0.5) * 1.2))


class EfficientNetDetector:
    """EfficientNet-B4 binary (authentic vs. manipulated) frame classifier.

    Loads trained weights whose classifier head is a single logit. Kept lazy so
    torch stays an optional dependency.
    """

    name = "efficientnet"

    def __init__(self, weights_path: Optional[str], device: str = "cpu"):
        if not weights_path:
            raise FrameGuardError("efficientnet backend needs FRAMEGUARD_AI_WEIGHTS (trained weights)")
        try:
            import numpy as np  # noqa: F401
            import torch
            from torchvision import models
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise FrameGuardError(
                "efficientnet backend needs torch + torchvision + numpy; "
                "run 'pip install -r requirements-ai.txt'"
            ) from exc

        self._torch = torch
        self._np = np
        self._device = device
        self._input = 380  # EfficientNet-B4 native input size

        model = models.efficientnet_b4(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, 1)
        state = torch.load(weights_path, map_location=device)
        model.load_state_dict(state)
        model.eval().to(device)
        self._model = model
        self._mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        self._std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

    def score_frame(self, rgb: bytes, width: int, height: int) -> float:  # pragma: no cover - needs torch
        torch = self._torch
        arr = self._np.frombuffer(rgb, dtype=self._np.uint8).reshape(height, width, 3)
        tensor = torch.from_numpy(arr.copy()).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        tensor = torch.nn.functional.interpolate(
            tensor, size=(self._input, self._input), mode="bilinear", align_corners=False
        )
        tensor = (tensor - self._mean) / self._std
        with torch.no_grad():
            logit = self._model(tensor.to(self._device))
            return float(torch.sigmoid(logit).item())


def build_detector(config: Config) -> Optional[FrameDetector]:
    backend = (config.ai_backend or "none").lower()
    if backend in ("none", "", "off", "disabled"):
        return None
    if backend == "heuristic":
        return HeuristicBaselineDetector()
    if backend == "efficientnet":
        return EfficientNetDetector(config.ai_weights_path, config.ai_device)
    raise FrameGuardError(f"Unknown AI backend '{config.ai_backend}'")


def aggregate(frame_scores: Sequence[float]) -> dict:
    """Collapse per-frame probabilities into a video-level summary.

    Returns the mean manipulation score (0..100) and the indices of the most
    suspicious frames.
    """
    if not frame_scores:
        return {"manipulation_score": 0, "suspicious_frames": []}
    mean = sum(frame_scores) / len(frame_scores)
    ranked = sorted(range(len(frame_scores)), key=lambda i: frame_scores[i], reverse=True)
    # Only surface frames that are actually above the mean (avoid noise on clean clips).
    suspicious: List[int] = [i for i in ranked[:TOP_SUSPICIOUS] if frame_scores[i] > mean]
    return {"manipulation_score": round(mean * 100), "suspicious_frames": sorted(suspicious)}
