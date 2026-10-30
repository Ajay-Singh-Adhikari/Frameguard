"use client";

import { useEffect, useState } from "react";
import { Film, Loader2, ShieldQuestion } from "lucide-react";
import { verifyVideo } from "@/lib/api";
import type { VerifyReport } from "@/lib/types";
import { formatBytes } from "@/lib/format";

export default function VerifyPanel({
  initialVideoId,
  onVerified,
}: {
  initialVideoId: string;
  onVerified: (report: VerifyReport) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [videoId, setVideoId] = useState(initialVideoId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When a fresh registration completes, pre-fill the id to verify.
  useEffect(() => {
    if (initialVideoId) setVideoId(initialVideoId);
  }, [initialVideoId]);

  async function submit() {
    if (!file || !videoId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const report = await verifyVideo(file, videoId.trim());
      onVerified(report);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <ShieldQuestion size={18} />
        </span>
        <div>
          <h2 className="text-base font-semibold">2 · Verify</h2>
          <p className="text-xs text-muted">Rebuild the root and localize tampered frames.</p>
        </div>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-surface-2 px-4 py-6 text-center transition hover:border-primary/60">
        <Film size={22} className="text-muted" />
        <span className="text-sm">
          {file ? <span className="font-medium">{file.name}</span> : "Choose the received copy to verify"}
        </span>
        {file && <span className="text-xs text-muted">{formatBytes(file.size)}</span>}
        <input
          type="file"
          accept="video/*,.mkv"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <div className="mt-4">
        <label className="mb-1.5 block text-xs text-muted" htmlFor="ver-id">
          Video ID to check against
        </label>
        <input
          id="ver-id"
          value={videoId}
          onChange={(e) => setVideoId(e.target.value)}
          placeholder="e.g. vid_1724ca3b14da_30fps"
          className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 font-data text-sm outline-none focus:border-primary/60"
        />
      </div>

      <button
        type="button"
        onClick={submit}
        disabled={!file || !videoId.trim() || loading}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-white transition enabled:hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <ShieldQuestion size={16} />}
        {loading ? "Rebuilding tree…" : "Verify video"}
      </button>

      {error && (
        <p className="mt-3 rounded-md border border-tampered/40 bg-tampered/10 px-3 py-2 text-sm text-tampered">
          {error}
        </p>
      )}
    </section>
  );
}
