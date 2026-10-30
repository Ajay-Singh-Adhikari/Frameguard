import type { Health, RegisterResult, VerifyReport } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function parseError(res: Response): Promise<never> {
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (body?.detail) {
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    /* response had no JSON body */
  }
  throw new Error(detail);
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function registerVideo(
  file: File,
  targetFps: number,
  videoId?: string,
): Promise<RegisterResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("target_fps", String(targetFps));
  if (videoId) form.append("video_id", videoId);

  const res = await fetch(`${API_BASE}/register`, { method: "POST", body: form });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function verifyVideo(file: File, videoId: string): Promise<VerifyReport> {
  const form = new FormData();
  form.append("file", file);
  form.append("video_id", videoId);

  const res = await fetch(`${API_BASE}/verify`, { method: "POST", body: form });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function fetchReportPdf(report: VerifyReport): Promise<Blob> {
  const res = await fetch(`${API_BASE}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!res.ok) return parseError(res);
  return res.blob();
}
