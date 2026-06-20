export type FreshnessColor = "emerald" | "green" | "amber" | "orange" | "red" | "zinc";

export interface JobResult {
  id: number;
  source: string;
  external_id: string;
  title: string;
  company: string;
  location: string | null;
  description: string | null;
  apply_url: string;
  posted_at: string | null;
  employment_type: string | null;
  skills: string[];
  hours_old: number | null;
  freshness_score: number;
  freshness_label: string;
  freshness_color: FreshnessColor;
  est_applicants: string;
  velocity_label: string | null;
  bookmark_status: "bookmarked" | "applied" | "dismissed" | null;
  // Phase 2 — enriched
  is_remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  tags: string[];
  // Phase 3 — semantic ranking
  semantic_score: number | null;
}

export interface JobSearch {
  id: number;
  name: string;
  query: string;
  location: string | null;
  remote_only: boolean;
  experience: string | null;
  freshness_hours: number;
  is_active: boolean;
  last_alerted_at: string | null;
  created_at: string;
}

export interface JobSearchCreate {
  name: string;
  query: string;
  location?: string;
  remote_only?: boolean;
  experience?: string;
  freshness_hours?: number;
}

export interface SearchParams {
  q: string;
  location?: string;
  remote_only?: boolean;
  experience?: string;
  employment_type?: string;  // client-side filter only
}

export interface ApplyAndTrackResponse {
  bookmark_id: number;
  application_id: number;
}
