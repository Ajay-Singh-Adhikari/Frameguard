export interface VideoSource {
  filename: string;
  file_size: number;
  file_sha256: string;
  container?: string | null;
  codec?: string | null;
  pixel_format?: string | null;
  width: number;
  height: number;
  native_fps: number;
  duration_seconds?: number | null;
  native_frame_count?: number | null;
  creation_time?: string | null;
}

export interface StoredObject {
  cid: string;
  size?: number | null;
  backend: string;
  gateway_url: string;
}

export interface IpfsInfo {
  backend: string;
  video: StoredObject;
  manifest: StoredObject;
}

export interface RegisterResult {
  video_id: string;
  merkle_root: string;
  frame_count: number;
  target_fps: number;
  metadata_hash: string;
  manifest_path: string;
  anchor: Record<string, unknown>;
  ipfs?: IpfsInfo | null;
  source: VideoSource;
}

export interface VerifyReport {
  video_id: string;
  target_fps: number;
  integrity: "INTACT" | "TAMPERED";
  root_match: boolean;
  anchored_root: string;
  recomputed_root: string;
  manifest_intact: boolean;
  original_frame_count: number;
  received_frame_count: number;
  frame_count_match: boolean;
  tampered_frames: number[];
  intact_frame_count: number;
  crypto_integrity_score: number;
  ai_manipulation_score: number | null;
  ai_backend?: string;
  ai_suspicious_frames?: number[];
  hybrid_trust_score: number;
  crypto_weight: number;
  notes: string[];
  checked_at: string;
}

export interface Health {
  status: string;
  version: string;
  frame_backend: string;
  anchor_backend: string;
  ai_backend?: string;
  storage_backend?: string;
  allowed_fps: number[];
}
