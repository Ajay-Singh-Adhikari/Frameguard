"use client";

import { useState } from "react";
import { CheckCircle2, Film, Loader2, UploadCloud } from "lucide-react";
import { registerVideo } from "@/lib/api";
import type { RegisterResult } from "@/lib/types";
import { formatBytes, shortHash } from "@/lib/format";

export default function RegisterPanel({
  allowedFps,
  onRegistered,
}: {
  allowedFps: number[];
  onRegistered: (result: RegisterResult) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [fps, setFps] = useState<number>(allowedFps.includes(30) ? 30 : allowedFps[0] ?? 30);
  const [videoId, setVideoId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RegisterResult | null>(null);

  async function submit() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await registerVideo(file, fps, videoId.trim() || undefined);
      setResult(r);
      onRegistered(r);
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
          <UploadCloud size={18} />
        </span>
        <div>
          <h2 className="text-base font-semibold">1 · Register</h2>
          <p className="text-xs text-muted">Hash every frame and anchor the Merkle root.</p>
        </div>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-surface-2 px-4 py-6 text-center transition hover:border-primary/60">
        <Film size={22} className="text-muted" />
        <span className="text-sm">
          {file ? <span className="font-medium">{file.name}</span> : "Choose a video to register"}
        </span>
        {file && <span className="text-xs text-muted">{formatBytes(file.size)}</span>}
        <input
          type="file"
          accept="video/*,.mkv"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <div className="mt-4 space-y-3">
        <div>
          <span className="mb-1.5 block text-xs text-muted">Sampling rate</span>
          <div className="flex gap-2">
            {allowedFps.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setFps(value)}
                className={`rounded-md border px-3 py-1.5 text-sm transition ${
                  fps === value
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted hover:text-foreground"
                }`}
              >
                {value} fps
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs text-muted" htmlFor="reg-id">
            Video ID <span className="opacity-60">(optional)</span>
          </label>
          <input
            id="reg-id"
            value={videoId}
            onChange={(e) => setVideoId(e.target.value)}
            placeholder="auto-generated from the file hash"
            className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 font-data text-sm outline-none focus:border-primary/60"
          />
        </div>
      </div>

      <button
        type="button"
        onClick={submit}
        disabled={!file || loading}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-white transition enabled:hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <UploadCloud size={16} />}
        {loading ? "Hashing frames…" : "Register video"}
      </button>

      {error && (
        <p className="mt-3 rounded-md border border-tampered/40 bg-tampered/10 px-3 py-2 text-sm text-tampered">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4 rounded-lg border border-intact/30 bg-intact/5 p-3 text-sm">
          <p className="flex items-center gap-1.5 font-medium text-intact">
            <CheckCircle2 size={16} /> Registered
          </p>
          <dl className="mt-2 space-y-1 text-xs">
            <Row label="Video ID" value={result.video_id} mono />
            <Row label="Frames" value={`${result.frame_count} @ ${result.target_fps} fps`} />
            <Row label="Merkle root" value={shortHash(result.merkle_root)} mono />
            <Row
              label="Source"
              value={`${result.source.width}×${result.source.height} · ${result.source.codec ?? "?"}`}
            />
          </dl>
          {result.ipfs && (
            <div className="mt-2 border-t border-border pt-2 text-xs">
              <p className="mb-1 text-muted">IPFS ({result.ipfs.backend})</p>
              <a
                href={result.ipfs.video.gateway_url}
                target="_blank"
                rel="noreferrer"
                className="block truncate font-data text-primary hover:underline"
                title={result.ipfs.video.cid}
              >
                video: {shortHash(result.ipfs.video.cid)}
              </a>
              <a
                href={result.ipfs.manifest.gateway_url}
                target="_blank"
                rel="noreferrer"
                className="block truncate font-data text-primary hover:underline"
                title={result.ipfs.manifest.cid}
              >
                manifest: {shortHash(result.ipfs.manifest.cid)}
              </a>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className={mono ? "font-data text-foreground" : "text-foreground"}>{value}</dd>
    </div>
  );
}
