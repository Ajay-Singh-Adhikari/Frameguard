from frameguard.report import build_report_pdf


def _report(integrity: str = "TAMPERED") -> dict:
    intact = integrity == "INTACT"
    return {
        "video_id": "demo_clip",
        "target_fps": 15,
        "integrity": integrity,
        "root_match": intact,
        "anchored_root": "ab" * 32,
        "recomputed_root": ("ab" if intact else "cd") * 32,
        "manifest_intact": True,
        "original_frame_count": 30,
        "received_frame_count": 30,
        "frame_count_match": True,
        "tampered_frames": [] if intact else [15, 16, 17],
        "intact_frame_count": 30 if intact else 27,
        "crypto_integrity_score": 100 if intact else 90,
        "ai_manipulation_score": None,
        "hybrid_trust_score": 100 if intact else 90,
        "crypto_weight": 0.6,
        "notes": [] if intact else ["Frame count changed."],
        "checked_at": "2026-10-29T00:00:00+00:00",
    }


def test_report_pdf_is_a_pdf():
    pdf = build_report_pdf(_report("TAMPERED"))
    assert isinstance(pdf, (bytes, bytearray))
    assert bytes(pdf).startswith(b"%PDF")
    assert len(pdf) > 1000


def test_report_pdf_intact_variant():
    pdf = build_report_pdf(_report("INTACT"))
    assert bytes(pdf).startswith(b"%PDF")
