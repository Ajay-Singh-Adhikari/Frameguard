from frameguard.metadata import ExtractionParams, VideoMetadata, compute_metadata_hash


def _meta():
    return VideoMetadata(
        filename="clip.mkv", file_size=123, file_sha256="ab" * 32,
        width=64, height=64, native_fps=30.0,
    )


def test_metadata_hash_is_stable_and_binds_fields():
    meta, extraction = _meta(), ExtractionParams(target_fps=15, frame_backend="ffmpeg")
    h1 = compute_metadata_hash(meta, extraction, 10, "root")
    h2 = compute_metadata_hash(meta, extraction, 10, "root")
    assert h1 == h2 and len(h1) == 64
    # Changing any bound field changes the hash.
    assert compute_metadata_hash(meta, extraction, 11, "root") != h1
    assert compute_metadata_hash(meta, extraction, 10, "other") != h1
