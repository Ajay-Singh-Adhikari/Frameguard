"use client";

import { useState } from "react";
import { AlertTriangle, Download, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import type { VerifyReport } from "@/lib/types";
import { fetchReportPdf } from "@/lib/api";
import { shortHash } from "@/lib/format";
import FrameTimeline from "./FrameTimeline";

export default function ResultPanel({ report }: { report: VerifyReport }) {
  const intact = report.integrity === "INTACT";
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState<string | null>(null);

  async function downloadReport() {
    setDownloading(true);
    setDlError(null);
    try {
      const blob = await fetchReportPdf(report);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `frameguard-${report.video_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setDlError(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      {/* Toolbar */}
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">Verification result</h3>
        <button
          type="button"
          onClick={downloadReport}
          disabled={downloading}
          className="flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium transition enabled:hover:border-primary/60 disabled:opacity-50"
        >
          {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          {downloading ? "Preparing…" : "Download PDF report"}
        </button>
      </div>
      {dlError && (
        <p className="mb-3 rounded-md border border-tampered/40 bg-tampered/10 px-3 py-2 text-xs text-tampered">
          {dlError}
        </p>
      )}

      {/* Verdict */}
      <div
        className={`flex items-center justify-between gap-4 rounded-lg border p-4 ${
          intact ? "border-intact/40 bg-intact/10" : "border-tampered/40 bg-tampered/10"
        }`}
      >
        <div className="flex items-center gap-3">
          {intact ? (
            <ShieldCheck className="text-intact" size={28} />
          ) : (
            <ShieldAlert className="text-tampered" size={28} />
          )}
          <div>
            <p className={`text-lg font-semibold ${intact ? "text-intact" : "text-tampered"}`}>
              {intact ? "INTACT" : "TAMPERED"}
            </p>
            <p className="text-xs text-muted">
              {intact
                ? "The rebuilt Merkle root matches the anchor."
                : `${report.tampered_frames.length} frame(s) differ from the anchored video.`}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${intact ? "text-intact" : "text-tampered"}`}>
            {report.hybrid_trust_score}
          </p>
          <p className="text-[10px] uppercase tracking-wide text-muted">Trust score</p>
        </div>
      </div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Root match" value={report.root_match ? "Yes" : "No"} good={report.root_match} />
        <Stat
          label="Frames"
          value={`${report.received_frame_count} / ${report.original_frame_count}`}
          good={report.frame_count_match}
        />
        <Stat label="Crypto score" value={`${report.crypto_integrity_score}`} good={intact} />
        <Stat
          label="AI manip."
          value={report.ai_manipulation_score === null ? "n/a" : `${report.ai_manipulation_score}`}
          good={report.ai_manipulation_score !== null ? report.ai_manipulation_score < 50 : undefined}
          muted={report.ai_manipulation_score === null}
        />
      </div>

      {/* Roots */}
      <div className="mt-4 space-y-1.5 rounded-lg border border-border bg-surface-2 p-3 text-xs">
        <RootRow label="Anchored root" value={report.anchored_root} />
        <RootRow label="Rebuilt root" value={report.recomputed_root} match={report.root_match} />
      </div>

      {/* Timeline */}
      <div className="mt-5">
        <h3 className="mb-2 text-sm font-semibold">Frame timeline</h3>
        <FrameTimeline
          total={report.original_frame_count}
          tampered={report.tampered_frames}
          fps={report.target_fps}
        />
      </div>

      {report.notes.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {report.notes.map((note, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted">
              <AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-400" />
              <span>{note}</span>
            </li>
          ))}
        </ul>
      )}

      {report.ai_manipulation_score === null ? (
        <p className="mt-4 text-[11px] text-muted">
          Verdict is cryptographic only. The EfficientNet-B4 content-manipulation score (fused at a
          {" "}
          {report.crypto_weight.toFixed(1)}/{(1 - report.crypto_weight).toFixed(1)} weight) is a later phase.
        </p>
      ) : (
        <p className="mt-4 text-[11px] text-muted">
          Hybrid score fuses cryptographic ({report.crypto_weight.toFixed(1)}) and AI (
          {(1 - report.crypto_weight).toFixed(1)}) evidence · AI backend: {report.ai_backend ?? "?"}
          {report.ai_backend === "baseline-heuristic" && " (placeholder, not a trained model)"}.
        </p>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  good,
  muted,
}: {
  label: string;
  value: string;
  good?: boolean;
  muted?: boolean;
}) {
  const color = muted ? "text-muted" : good ? "text-intact" : "text-tampered";
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <p className="text-[10px] uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${color}`}>{value}</p>
    </div>
  );
}

function RootRow({ label, value, match }: { label: string; value: string; match?: boolean }) {
  const color = match === undefined ? "text-foreground" : match ? "text-intact" : "text-tampered";
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className={`font-data ${color}`} title={value}>
        {shortHash(value)}
      </span>
    </div>
  );
}
