const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface StartSessionRequest {
  topic: string;
  role: string;
  years_exp: string;
  num_questions: number;
  difficulty: "easy" | "medium" | "hard";
  jd_text?: string;
  custom_questions?: string[];
}

export interface StartSessionResponse {
  session_id: number;
  questions: string[];
  total_questions: number;
}

export interface QuestionReport {
  question_index: number;
  question: string;
  user_answer: string;
  ideal_answer: string;
  score: number;
  feedback: string;
}

export interface InterviewReportResponse {
  status: "ready" | "pending";
  session?: {
    id: number;
    topic: string;
    role: string;
    years_exp: string;
    duration_min: number;
    created_at: string;
  };
  overall_score?: number;
  skill_breakdown?: Record<string, number>;
  summary?: string;
  questions?: QuestionReport[];
}

export interface HistoryItem {
  id: number;
  topic: string;
  role: string;
  years_exp: string;
  duration_min: number;
  status: string;
  created_at: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function startSession(body: StartSessionRequest): Promise<StartSessionResponse> {
  return apiFetch("/interview/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function submitTurn(
  sessionId: number,
  payload: { question_index: number; question: string; user_answer: string },
): Promise<void> {
  await apiFetch(`/interview/sessions/${sessionId}/turns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function endSession(sessionId: number): Promise<void> {
  await apiFetch(`/interview/sessions/${sessionId}/end`, { method: "POST" });
}

export async function getReport(sessionId: number): Promise<InterviewReportResponse> {
  return apiFetch(`/interview/sessions/${sessionId}/report`);
}

export async function getHistory(): Promise<HistoryItem[]> {
  return apiFetch("/interview/history");
}

export async function deleteSession(sessionId: number): Promise<void> {
  await apiFetch(`/interview/sessions/${sessionId}`, { method: "DELETE" });
}

// ── Agent mode ────────────────────────────────────────────────────────────────

export interface StartAgentSessionRequest {
  topic: string;
  role: string;
  years_exp: string;
  difficulty: "easy" | "medium" | "hard";
  target_turns: number;
  jd_text?: string;
}

export interface StartAgentSessionResponse {
  session_id: number;
  thread_id: string;
  first_question: string;
  topic_clusters: string[];
  target_turns: number;
  agent_mode: true;
}

export interface SubmitAnswerResponse {
  next_question: string | null;
  question_number: number;
  followup_depth: number;
  interview_complete: boolean;
  agent_status: "asking" | "wrapping_up" | "done";
}

export async function startAgentSession(
  body: StartAgentSessionRequest,
): Promise<StartAgentSessionResponse> {
  return apiFetch("/interview/sessions/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function submitAnswer(
  sessionId: number,
  answer: string,
): Promise<SubmitAnswerResponse> {
  return apiFetch(`/interview/sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
}
