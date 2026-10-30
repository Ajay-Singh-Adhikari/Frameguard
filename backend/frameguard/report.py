"""Render a one-page PDF verification report from a verify result.

The report mirrors the dashboard: a verdict banner, the cryptographic evidence
(both Merkle roots, frame counts), a drawn frame-level timeline, the scores, and
the source/registration metadata. It is produced with fpdf2 (pure Python), so it
works anywhere the backend runs and is reused by the CLI and the HTTP API.
"""
from __future__ import annotations

from typing import List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .metadata import Manifest

# Palette (matches the dashboard tokens)
INTACT = (34, 197, 94)
TAMPERED = (239, 68, 68)
INK = (23, 29, 38)
MUTED = (120, 132, 148)
LIGHT = (240, 243, 247)
BORDER = (210, 216, 224)

PAGE_W = 210
MARGIN = 15
USABLE = PAGE_W - 2 * MARGIN  # 180 mm


def _ascii(text: str) -> str:
    """Core PDF fonts are latin-1 only; drop anything that cannot be encoded."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _ranges(indices: List[int]) -> str:
    if not indices:
        return "none"
    sorted_idx = sorted(indices)
    parts: List[str] = []
    start = prev = sorted_idx[0]
    for x in sorted_idx[1:]:
        if x == prev + 1:
            prev = x
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = x
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(parts)


def build_report_pdf(
    report: dict,
    *,
    anchor: Optional[dict] = None,
    manifest: Optional[Manifest] = None,
) -> bytes:
    intact = report.get("integrity") == "INTACT"
    accent = INTACT if intact else TAMPERED

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.add_page()

    def line_break_cell(w, h, txt, font=("Helvetica", "", 9), color=INK, align="L"):
        pdf.set_font(*font)
        pdf.set_text_color(*color)
        pdf.cell(w, h, _ascii(str(txt)), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)

    def kv(label: str, value, mono: bool = False):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(52, 6, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Courier" if mono else "Helvetica", "", 9)
        pdf.set_text_color(*INK)
        pdf.cell(0, 6, _ascii(str(value)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section(title: str):
        pdf.ln(3)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*INK)
        pdf.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.3)
        y = pdf.get_y()
        pdf.line(MARGIN, y, PAGE_W - MARGIN, y)
        pdf.ln(1)

    # --- Header ---
    line_break_cell(0, 10, "FrameGuard", font=("Helvetica", "B", 20))
    line_break_cell(
        0, 6, "Frame-level video tamper detection - verification report",
        font=("Helvetica", "", 11), color=MUTED,
    )
    pdf.ln(1)

    # --- Verdict banner ---
    box_y = pdf.get_y()
    pdf.set_fill_color(*accent)
    pdf.rect(MARGIN, box_y, USABLE, 20, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(MARGIN + 4, box_y + 3)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(120, 7, "INTACT" if intact else "TAMPERED", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_xy(MARGIN + 4, box_y + 11)
    pdf.set_font("Helvetica", "", 9)
    subtitle = (
        "Rebuilt Merkle root matches the anchor."
        if intact
        else f"{len(report.get('tampered_frames', []))} frame(s) differ from the anchored video."
    )
    pdf.cell(120, 5, _ascii(subtitle), new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_xy(PAGE_W - MARGIN - 50, box_y + 2)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(46, 11, str(report.get("hybrid_trust_score", "-")), align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_xy(PAGE_W - MARGIN - 50, box_y + 14)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(46, 4, "TRUST SCORE / 100", align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_xy(MARGIN, box_y + 24)

    # --- Cryptographic evidence ---
    section("Cryptographic evidence")
    kv("Video ID", report.get("video_id", ""), mono=True)
    kv("Checked at", report.get("checked_at", ""))
    kv("Sampling rate", f"{report.get('target_fps', '?')} fps")
    kv("Root match", "Yes" if report.get("root_match") else "No")
    kv("Anchored root", report.get("anchored_root", ""), mono=True)
    kv("Rebuilt root", report.get("recomputed_root", ""), mono=True)
    kv(
        "Frames (received/anchored)",
        f"{report.get('received_frame_count', '?')} / {report.get('original_frame_count', '?')}",
    )
    kv("Manifest intact", "Yes" if report.get("manifest_intact") else "No")

    # --- Frame timeline ---
    section("Frame timeline")
    total = int(report.get("original_frame_count") or 0)
    tampered = set(report.get("tampered_frames") or [])
    fps = float(report.get("target_fps") or 0)
    bar_y = pdf.get_y() + 1
    bar_h = 10
    pdf.set_fill_color(*INTACT)
    pdf.rect(MARGIN, bar_y, USABLE, bar_h, "F")
    if total > 0 and tampered:
        max_seg = 540
        bucketed = total > max_seg
        count = max_seg if bucketed else total
        per = total / count
        seg_w = USABLE / count
        pdf.set_fill_color(*TAMPERED)
        for i in range(count):
            if bucketed:
                frm = int(i * per)
                to = max(frm, int((i + 1) * per) - 1)
                hit = any(f in tampered for f in range(frm, to + 1))
            else:
                hit = i in tampered
            if hit:
                pdf.rect(MARGIN + i * seg_w, bar_y, seg_w + 0.15, bar_h, "F")
    pdf.set_draw_color(*BORDER)
    pdf.rect(MARGIN, bar_y, USABLE, bar_h, "D")
    pdf.set_y(bar_y + bar_h + 1)

    duration = total / fps if fps else 0
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.set_x(MARGIN)
    pdf.cell(USABLE / 2, 5, "0.0s", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(USABLE / 2, 5, f"{duration:.1f}s", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    kv("Altered frames", _ranges(sorted(tampered)))

    # --- Scores ---
    section("Scores")
    kv("Cryptographic integrity", f"{report.get('crypto_integrity_score', '?')} / 100")
    ai = report.get("ai_manipulation_score")
    ai_backend = report.get("ai_backend", "none")
    if ai is None:
        kv("AI content manipulation", "n/a (backend: none)")
    else:
        kv("AI content manipulation", f"{ai} / 100 ({ai_backend})")
        susp = report.get("ai_suspicious_frames") or []
        if susp:
            kv("AI-flagged frames", _ranges(sorted(susp)))
    kv("Hybrid trust score", f"{report.get('hybrid_trust_score', '?')} / 100")
    kv("Cryptographic weight", report.get("crypto_weight", ""))

    # --- Source & registration ---
    if manifest is not None or anchor is not None:
        section("Source & registration")
        if manifest is not None:
            m = manifest.metadata
            kv("Filename", m.filename)
            kv("Codec / container", f"{m.codec} / {m.container}")
            kv("Resolution", f"{m.width} x {m.height}")
            kv("Native fps", m.native_fps)
            kv("Duration", f"{m.duration_seconds}s" if m.duration_seconds else "n/a")
            kv("File SHA-256", m.file_sha256, mono=True)
        if anchor is not None:
            kv("Registered at", anchor.get("registered_at") or anchor.get("timestamp") or "")
            kv("Registrant", anchor.get("registrant", ""), mono=True)
            kv("Metadata hash", anchor.get("metadata_hash", ""), mono=True)
            kv("Anchor backend", anchor.get("backend", ""))

    # --- Notes ---
    notes = report.get("notes") or []
    if notes:
        section("Notes")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*INK)
        for note in notes:
            pdf.set_x(MARGIN)
            pdf.multi_cell(0, 5, _ascii(f"- {note}"))

    # --- Footer ---
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*MUTED)
    pdf.set_x(MARGIN)
    if report.get("ai_manipulation_score") is None:
        footer = (
            "This verdict is cryptographic only. The EfficientNet-B4 content-manipulation "
            "score is a later phase. Generated by FrameGuard."
        )
    else:
        cw = report.get("crypto_weight", 0.6)
        footer = (
            f"Hybrid trust score fuses cryptographic ({cw}) and AI ({round(1 - cw, 2)}) evidence. "
            f"AI backend: {report.get('ai_backend', 'none')}. Generated by FrameGuard."
        )
    pdf.multi_cell(0, 4, _ascii(footer))

    return bytes(pdf.output())
