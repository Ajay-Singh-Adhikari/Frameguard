"use client";

import { useMemo } from "react";
import { compressRanges } from "@/lib/format";

const MAX_SEGMENTS = 1600; // above this we bucket, so the DOM stays light for long videos

interface Segment {
  tampered: boolean;
  from: number;
  to: number;
}

export default function FrameTimeline({
  total,
  tampered,
  fps,
}: {
  total: number;
  tampered: number[];
  fps: number;
}) {
  const tamperedSet = useMemo(() => new Set(tampered), [tampered]);

  const segments = useMemo<Segment[]>(() => {
    if (total <= 0) return [];
    const bucketed = total > MAX_SEGMENTS;
    const count = bucketed ? MAX_SEGMENTS : total;
    const per = total / count;
    return Array.from({ length: count }, (_, i) => {
      if (!bucketed) return { tampered: tamperedSet.has(i), from: i, to: i };
      const from = Math.floor(i * per);
      const to = Math.max(from, Math.floor((i + 1) * per) - 1);
      let hit = false;
      for (let f = from; f <= to; f++) {
        if (tamperedSet.has(f)) {
          hit = true;
          break;
        }
      }
      return { tampered: hit, from, to };
    });
  }, [total, tamperedSet]);

  const durationSec = fps > 0 ? total / fps : 0;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between text-xs text-muted">
        <span>
          {total} frames · {durationSec.toFixed(1)}s @ {fps} fps
        </span>
        <span>
          <span className="text-tampered font-medium">{tampered.length}</span> altered
        </span>
      </div>

      {/* The timeline bar: one cell per frame (bucketed for long clips) */}
      <div className="flex h-12 w-full overflow-hidden rounded-md border border-border bg-surface-2">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={seg.tampered ? "bg-tampered" : "bg-intact/70"}
            style={{ flex: "1 1 0%", minWidth: 0 }}
            title={
              (seg.from === seg.to ? `Frame ${seg.from}` : `Frames ${seg.from}–${seg.to}`) +
              (seg.tampered ? " — altered" : " — intact")
            }
          />
        ))}
      </div>

      {/* Time axis */}
      <div className="mt-1 flex justify-between font-data text-[10px] text-muted">
        {ticks.map((t) => (
          <span key={t}>{(durationSec * t).toFixed(1)}s</span>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-sm bg-intact/70" /> intact
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-sm bg-tampered" /> altered
        </span>
        {tampered.length > 0 && (
          <span className="text-muted">
            altered frames: <span className="font-data text-foreground">{compressRanges(tampered)}</span>
          </span>
        )}
      </div>
    </div>
  );
}
