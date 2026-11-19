import type { Health, QueueItem, ReviewRequest, ReviewResponse, SampleMeta, Stats, Triage } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new ApiError("Cannot reach the BitReview server. Check your connection and try again.", 0);
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail)) msg = j.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch { /* non-JSON error body */ }
    throw new ApiError(msg, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => call<Health>("/api/health"),
  stats: () => call<Stats>("/api/stats"),
  queue: (triage?: Triage) => call<QueueItem[]>(`/api/queue${triage ? `?triage=${triage}` : ""}`),
  samples: () => call<SampleMeta[]>("/api/samples"),
  review: (body: ReviewRequest) => call<ReviewResponse>("/api/review", { method: "POST", body: JSON.stringify(body) }),
  getReview: (id: string) => call<ReviewResponse>(`/api/reviews/${encodeURIComponent(id)}`),
};
