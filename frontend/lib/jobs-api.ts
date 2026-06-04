import type {
  ApplyAndTrackResponse,
  JobResult,
  JobSearch,
  JobSearchCreate,
  SearchParams,
} from "@/types/jobs";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function searchJobs(params: SearchParams): Promise<JobResult[]> {
  const qs = new URLSearchParams();
  qs.set("q", params.q);
  if (params.location) qs.set("location", params.location);
  if (params.remote_only) qs.set("remote_only", "true");
  if (params.experience) qs.set("experience", params.experience);
  if (params.freshness_hours) qs.set("freshness_hours", String(params.freshness_hours));
  if (params.page) qs.set("page", String(params.page));
  return apiFetch(`/jobs/search?${qs.toString()}`);
}

export async function listSavedSearches(): Promise<JobSearch[]> {
  return apiFetch("/jobs/searches");
}

export async function createSavedSearch(body: JobSearchCreate): Promise<JobSearch> {
  return apiFetch("/jobs/searches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteSavedSearch(id: number): Promise<void> {
  return apiFetch(`/jobs/searches/${id}`, { method: "DELETE" });
}

export interface MatchResult {
  score: number | null;
  grade: string | null;
  top_missing: string[];
  reason?: string;
}

export async function matchResume(jobCacheId: number): Promise<MatchResult> {
  return apiFetch(`/jobs/${jobCacheId}/match`);
}

export async function atsJobScan(jobCacheId: number): Promise<unknown> {
  return apiFetch(`/jobs/${jobCacheId}/ats-scan`, { method: "POST" });
}

export async function bookmarkJob(jobCacheId: number): Promise<{ bookmark_id: number }> {
  return apiFetch(`/jobs/bookmark/${jobCacheId}`, { method: "POST" });
}

export async function applyAndTrack(payload: {
  job_cache_id: number;
  title: string;
  company: string;
  apply_url: string;
  posted_at: string | null;
  source: string;
  external_id: string;
  description?: string | null;
}): Promise<ApplyAndTrackResponse> {
  return apiFetch("/jobs/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
