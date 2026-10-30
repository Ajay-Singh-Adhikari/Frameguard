"use client";

import { useEffect, useState } from "react";
import { ScanLine, Server } from "lucide-react";
import { getHealth } from "@/lib/api";
import type { Health, RegisterResult, VerifyReport } from "@/lib/types";
import RegisterPanel from "@/components/RegisterPanel";
import VerifyPanel from "@/components/VerifyPanel";
import ResultPanel from "@/components/ResultPanel";

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [lastVideoId, setLastVideoId] = useState("");
  const [report, setReport] = useState<VerifyReport | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setHealthError(e instanceof Error ? e.message : String(e)));
  }, []);

  const allowedFps = health?.allowed_fps ?? [15, 30];

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 sm:px-6">
      {/* Header */}
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <ScanLine size={24} />
          </span>
          <div>
            <h1 className="text-xl font-bold tracking-tight">FrameGuard</h1>
            <p className="text-xs text-muted">Frame-level video tamper detection, anchored on a Merkle root.</p>
          </div>
        </div>
        <div
          className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${
            healthError
              ? "border-tampered/40 bg-tampered/10 text-tampered"
              : "border-border bg-surface text-muted"
          }`}
        >
          <Server size={13} />
          {health ? (
            <span>
              backend up · {health.frame_backend} · {health.anchor_backend} · ai:{health.ai_backend ?? "none"} ·
              ipfs:{health.storage_backend ?? "none"}
            </span>
          ) : healthError ? (
            <span>backend unreachable</span>
          ) : (
            <span>checking backend…</span>
          )}
        </div>
      </header>

      {healthError && (
        <p className="mb-6 rounded-lg border border-tampered/40 bg-tampered/10 px-4 py-3 text-sm text-tampered">
          Could not reach the API. Start it with{" "}
          <code className="font-data">python -m frameguard serve</code> and make sure it is on the URL in{" "}
          <code className="font-data">NEXT_PUBLIC_API_URL</code>.
        </p>
      )}

      {/* Panels */}
      <div className="grid gap-5 md:grid-cols-2">
        <RegisterPanel allowedFps={allowedFps} onRegistered={(r: RegisterResult) => setLastVideoId(r.video_id)} />
        <VerifyPanel initialVideoId={lastVideoId} onVerified={setReport} />
      </div>

      {/* Verdict + timeline */}
      {report && (
        <div className="mt-5">
          <ResultPanel report={report} />
        </div>
      )}

      <footer className="mt-10 text-center text-xs text-muted">
        Register a video, then verify the same or a tampered copy. The timeline marks the exact frames that differ.
      </footer>
    </main>
  );
}
