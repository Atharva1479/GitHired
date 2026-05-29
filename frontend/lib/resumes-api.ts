const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface ResumeOut {
  id: number;
  user_id: number;
  name: string;
  role_tag: string;
  file_name: string;
  created_at: string;
}

export interface SkillGap {
  skill: string;
  frequency: number;
  total_jobs: number;
}

export interface SkillGapResult {
  resume_id: number;
  resume_name: string;
  role_tag: string;
  matched_jobs: number;
  gaps: SkillGap[];
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { credentials: "include", ...init });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function listResumes(): Promise<ResumeOut[]> {
  return apiFetch("/resumes");
}

export async function uploadResume(
  name: string,
  roleTag: string,
  file: File
): Promise<ResumeOut> {
  const form = new FormData();
  form.append("name", name);
  form.append("role_tag", roleTag);
  form.append("file", file);
  return apiFetch("/resumes", { method: "POST", body: form });
}

export async function deleteResume(id: number): Promise<void> {
  await apiFetch(`/resumes/${id}`, { method: "DELETE" });
}

export async function getSkillGap(resumeId: number): Promise<SkillGapResult> {
  return apiFetch(`/resumes/${resumeId}/gap`);
}
