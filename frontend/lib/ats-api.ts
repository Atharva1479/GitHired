import type { AnalysisResult, TailorResult } from "@/types/ats";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function analyzeResume(formData: FormData): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/ats/analyze`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`);
  }
  return res.json() as Promise<AnalysisResult>;
}

export interface ATSFeedback {
  strengths: string[];
  suggestions: string[];
  weaknesses: string[];
}

export async function getAtsFeedback(result: AnalysisResult): Promise<ATSFeedback> {
  const body = {
    overall_score: result.overall_score,
    required_missing: result.required_missing,
    preferred_missing: result.preferred_missing,
    sections_found: result.sections.found,
    sections_missing: result.sections.missing,
    ats_risks: result.sections.ats_risks,
    suggestions: result.suggestions,
  };
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000); // 45s max
  try {
    const res = await fetch(`${BASE}/ats/ai-feedback`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`AI feedback error ${res.status}`);
    return res.json() as Promise<ATSFeedback>;
  } finally {
    clearTimeout(timeout);
  }
}

export interface TailorRequest {
  resume_text: string;
  jd_text: string;
  required_missing: string[];
  preferred_missing: string[];
}

export async function tailorResume(body: TailorRequest): Promise<TailorResult> {
  const res = await fetch(`${BASE}/ats/tailor`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Tailor error ${res.status}`);
  return res.json() as Promise<TailorResult>;
}
