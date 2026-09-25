// Hand-written client for the contract in the assignment (§2.2). Same-origin "/api": nginx (prod) or the
// Vite proxy (dev) forwards it, so no backend URL is baked into the bundle.
// Sync strategy: hand-mirrored from backend/app/schemas.py and app/domain.py (compared field by field on 2026-09-25).
// Nothing enforces this automatically yet; the tests mock responses. Regenerate from /openapi.json if the API changes.

export type Category = "water" | "electricity" | "sanitation" | "roads" | "streetlights" | "other";
export type Priority = "high" | "normal" | "low";
export type Status = "open" | "in_progress" | "resolved" | "rejected";

export const CATEGORIES: Category[] = ["water", "electricity", "sanitation", "roads", "streetlights", "other"];
export const PRIORITIES: Priority[] = ["high", "normal", "low"];
export const STATUSES: Status[] = ["open", "in_progress", "resolved", "rejected"];

export interface Complaint {
  id: string;
  text: string;
  location: string;
  reporter_contact: string | null;
  category: Category;
  priority: Priority;
  status: Status;
  ai_summary: string | null;
  triaged_by: string;
  triage_latency_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface ComplaintPage {
  items: Complaint[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  total: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface NewComplaint {
  text: string;
  location: string;
  reporter_contact?: string;
}

// Carries the server's own message (e.g. the 409 naming the attempted transition) and field errors (400).
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public retryAfter?: string | null,
  ) {
    super(message);
  }
}

function messageFrom(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e: { loc?: unknown[]; msg?: string }) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`).join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; headers: Headers }> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, `Request failed (${res.status})`), res.headers.get("Retry-After"));
  return { data: body as T, headers: res.headers };
}

export const createComplaint = (c: NewComplaint) =>
  request<Complaint>("/complaints", { method: "POST", body: JSON.stringify(c) }).then((r) => r.data);

export function listComplaints(q: { page: number; page_size: number; category?: string; priority?: string; status?: string }) {
  const p = new URLSearchParams();
  Object.entries(q).forEach(([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)));
  return request<ComplaintPage>(`/complaints?${p}`).then((r) => r.data);
}

export const setStatus = (id: string, status: Status) =>
  request<Complaint>(`/complaints/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }).then((r) => r.data);

export const getStats = () =>
  request<Stats>("/stats").then((r) => ({ stats: r.data, cache: r.headers.get("X-Cache") }));
