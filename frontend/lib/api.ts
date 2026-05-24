import type { AnalyticsStats } from "./analytics";
import type { SettingsPatch, UserSettings } from "./settings";
import type { ActivityItem, DashboardStats } from "./dashboard";
import type { Draft, DraftEntityType } from "./drafts";
import type { Nudge, NudgeSeverity } from "./nudges";
import type {
  ConnectionStatus,
  Referral,
  ReferralCreate,
  ReferralUpdate,
} from "./referrals";
import type {
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  DsaAnalysisOut,
  DsaProblemCreate,
  DsaProblemOut,
  DsaProblemUpdate,
  DsaStatsOut,
  FileKind,
  Status,
  StudyGenerateRequest,
  StudyGenerateResponse,
  StudyGenerateTopicsRequest,
  StudyGenerateTopicsResponse,
  StudyPlan,
  StudyProgress,
  StudyReviseResponse,
  StudySection,
  StudySectionCreate,
  StudySectionUpdate,
  StudySubsection,
  StudySubsectionCreate,
  StudySubsectionUpdate,
  StudyTopic,
  StudyTopicCreate,
  StudyTopicUpdate,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public status: number, public type: string, message: string) {
    super(message);
  }
}

function _maybeDispatchGamify(res: Response): void {
  if (typeof window === "undefined") return;
  const header = res.headers.get("X-Gamify");
  if (!header) return;
  try {
    const envelope = JSON.parse(header) as GamifyEnvelope;
    window.dispatchEvent(
      new CustomEvent<GamifyEnvelope>("jp:gamify", { detail: envelope }),
    );
  } catch {
    // ignore malformed payloads
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      type?: string;
      title?: string;
      detail?: string;
    };
    throw new ApiError(
      res.status,
      body.type ?? "error",
      body.detail || body.title || res.statusText,
    );
  }
  _maybeDispatchGamify(res);
  return res.status === 204 ? (null as T) : ((await res.json()) as T);
}

async function upload(path: string, file: File): Promise<Application> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      type?: string;
      title?: string;
      detail?: string;
    };
    throw new ApiError(
      res.status,
      body.type ?? "error",
      body.detail || body.title || res.statusText,
    );
  }
  _maybeDispatchGamify(res);
  return res.json();
}

export function fileUrl(id: number, kind: FileKind, download = false): string {
  return `${BASE}/applications/${id}/files/${kind}${download ? "?download=1" : ""}`;
}

export type Me = {
  id: number;
  email: string;
  display_name: string;
  picture_url: string | null;
  auto_brief_enabled?: boolean;
  /**
   * Per-login session identifier (UUID hex). Stays the same across
   * page refreshes; changes on logout/login. Frontend uses this to
   * decide "this is a fresh login, greet" vs "this is a refresh,
   * stay quiet".
   */
  session_id?: string | null;
};

export type GamifyEnvelope = {
  xp_gained: number;
  new_level: number | null;
  streak: number;
  quests_progressed: string[];
  quest_completed: string[];
  unlocked: string[];
  duplicate: boolean;
};

export type GamifyQuest = {
  code: string;
  title: string;
  target: number;
  progress: number;
  reward_xp: number;
  completed: boolean;
  expires_at: string;
};

export type GamifyUnlock = {
  code: string;
  title: string;
  unlocked_at: string;
  seen: boolean;
};

export type GamifyState = {
  xp: number;
  level: number;
  xp_into_level: number;
  xp_for_level: number;
  streak: number;
  longest_streak: number;
  freezes: number;
  unseen_level_up: number | null;
  daily_quests: GamifyQuest[];
  weekly_quests: GamifyQuest[];
  recent_unlocks: GamifyUnlock[];
};

export type Achievement = {
  code: string;
  title: string;
  unlocked_at: string | null;
};

export const googleLoginUrl = `${BASE}/auth/google/login`;

export const api = {
  auth: {
    me: () => request<Me>("/auth/me"),
    logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
    updatePreferences: (patch: { auto_brief_enabled: boolean }) =>
      request<{ auto_brief_enabled: boolean }>("/auth/preferences", {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
  },
  applications: {
    list: (params?: { status?: Status }) => {
      const q = params?.status
        ? `?status=${encodeURIComponent(params.status)}`
        : "";
      return request<Application[]>(`/applications${q}`);
    },
    get: (id: number) => request<Application>(`/applications/${id}`),
    create: (data: ApplicationCreate) =>
      request<Application>("/applications", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, patch: ApplicationUpdate) =>
      request<Application>(`/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    remove: (id: number) =>
      request<null>(`/applications/${id}`, { method: "DELETE" }),
    followup: (id: number) =>
      request<Application>(`/applications/${id}/followup`, { method: "POST" }),
    uploadFile: (id: number, kind: FileKind, file: File) =>
      upload(`/applications/${id}/files/${kind}`, file),
    deleteFile: (id: number, kind: FileKind) =>
      request<null>(`/applications/${id}/files/${kind}`, { method: "DELETE" }),
  },
  referrals: {
    list: (params?: { connection_status?: ConnectionStatus }) => {
      const q = params?.connection_status
        ? `?connection_status=${encodeURIComponent(params.connection_status)}`
        : "";
      return request<Referral[]>(`/referrals${q}`);
    },
    get: (id: number) => request<Referral>(`/referrals/${id}`),
    create: (data: ReferralCreate) =>
      request<Referral>("/referrals", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, patch: ReferralUpdate) =>
      request<Referral>(`/referrals/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    remove: (id: number) =>
      request<null>(`/referrals/${id}`, { method: "DELETE" }),
    markAccepted: (id: number) =>
      request<Referral>(`/referrals/${id}/mark-accepted`, { method: "POST" }),
    markSent: (id: number) =>
      request<Referral>(`/referrals/${id}/mark-sent`, { method: "POST" }),
    markReplied: (id: number) =>
      request<Referral>(`/referrals/${id}/mark-replied`, { method: "POST" }),
    linkApplication: (refId: number, appId: number) =>
      request<null>(`/referrals/${refId}/link-application/${appId}`, {
        method: "POST",
      }),
    unlinkApplication: (refId: number, appId: number) =>
      request<null>(`/referrals/${refId}/link-application/${appId}`, {
        method: "DELETE",
      }),
    linkedApplications: (id: number) =>
      request<Application[]>(`/referrals/${id}/applications`),
  },
  nudges: {
    list: (params?: { unread?: boolean; severity?: NudgeSeverity }) => {
      const q = new URLSearchParams();
      if (params?.unread != null) q.set("unread", String(params.unread));
      if (params?.severity) q.set("severity", params.severity);
      const s = q.toString();
      return request<Nudge[]>(`/nudges${s ? `?${s}` : ""}`);
    },
    today: () => request<Nudge[]>("/nudges/today"),
    markRead: (id: number) =>
      request<null>(`/nudges/${id}/read`, { method: "POST" }),
    markActed: (id: number) =>
      request<null>(`/nudges/${id}/acted`, { method: "POST" }),
    snooze: (id: number, days: number) =>
      request<null>(`/nudges/${id}/snooze`, {
        method: "POST",
        body: JSON.stringify({ days }),
      }),
    run: () => request<{ inserted: number }>("/nudges/run", { method: "POST" }),
  },
  drafts: {
    applicationFollowup: (id: number, regenerate = false) =>
      request<Draft>(`/drafts/application/${id}/followup`, {
        method: "POST",
        body: JSON.stringify({ regenerate }),
      }),
    referralAsk: (id: number, regenerate = false) =>
      request<Draft>(`/drafts/referral/${id}/ask`, {
        method: "POST",
        body: JSON.stringify({ regenerate }),
      }),
    referralFollowup: (id: number, regenerate = false) =>
      request<Draft>(`/drafts/referral/${id}/followup`, {
        method: "POST",
        body: JSON.stringify({ regenerate }),
      }),
    history: (entityType: DraftEntityType, entityId: number) =>
      request<Draft[]>(`/drafts/${entityType}/${entityId}/history`),
  },
  dashboard: {
    stats: () => request<DashboardStats>("/dashboard/stats"),
    activity: (limit = 15) =>
      request<ActivityItem[]>(`/dashboard/activity?limit=${limit}`),
  },
  gamify: {
    state: () => request<GamifyState>("/gamify/state"),
    acknowledge: () =>
      request<null>("/gamify/acknowledge", { method: "POST" }),
    achievements: () => request<Achievement[]>("/gamify/achievements"),
  },
  study: {
    plan: () => request<StudyPlan>("/study/plan"),
    progress: () => request<StudyProgress>("/study/progress"),
    listSections: () => request<StudySection[]>("/study/sections"),
    createSection: (data: StudySectionCreate) =>
      request<StudySection>("/study/sections", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateSection: (id: number, patch: StudySectionUpdate) =>
      request<StudySection>(`/study/sections/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    deleteSection: (id: number) =>
      request<null>(`/study/sections/${id}`, { method: "DELETE" }),
    createSubsection: (sectionId: number, data: StudySubsectionCreate) =>
      request<StudySubsection>(
        `/study/sections/${sectionId}/subsections`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    updateSubsection: (id: number, patch: StudySubsectionUpdate) =>
      request<StudySubsection>(`/study/subsections/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    deleteSubsection: (id: number) =>
      request<null>(`/study/subsections/${id}`, { method: "DELETE" }),
    createTopic: (subsectionId: number, data: StudyTopicCreate) =>
      request<StudyTopic>(
        `/study/subsections/${subsectionId}/topics`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    updateTopic: (id: number, patch: StudyTopicUpdate) =>
      request<StudyTopic>(`/study/topics/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    deleteTopic: (id: number) =>
      request<null>(`/study/topics/${id}`, { method: "DELETE" }),
    reviseTopic: (id: number) =>
      request<StudyReviseResponse>(`/study/topics/${id}/revise`, {
        method: "POST",
      }),
    unmarkTopic: (id: number) =>
      request<StudyTopic>(`/study/topics/${id}/unmark`, {
        method: "POST",
      }),
    generatePlan: (data: StudyGenerateRequest) =>
      request<StudyGenerateResponse>("/study/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    applyGeneratedPlan: (data: StudyGenerateResponse) =>
      request<StudyPlan>("/study/generate/apply", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateTopics: (subsectionId: number, data: StudyGenerateTopicsRequest) =>
      request<StudyGenerateTopicsResponse>(
        `/study/subsections/${subsectionId}/generate-topics`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    applyGeneratedTopics: (
      subsectionId: number,
      data: StudyGenerateTopicsResponse,
    ) =>
      request<StudyTopic[]>(
        `/study/subsections/${subsectionId}/generate-topics/apply`,
        { method: "POST", body: JSON.stringify(data) },
      ),
  },
  dsa: {
    stats: () =>
      request<DsaStatsOut>("/dsa/stats"),

    list: (topic?: string) =>
      request<DsaProblemOut[]>(`/dsa/problems${topic ? `?topic=${encodeURIComponent(topic)}` : ""}`),

    get: (id: number) =>
      request<DsaProblemOut>(`/dsa/problems/${id}`),

    create: (data: DsaProblemCreate) =>
      request<DsaProblemOut>("/dsa/problems", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: number, data: DsaProblemUpdate) =>
      request<DsaProblemOut>(`/dsa/problems/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    delete: (id: number) =>
      request<void>(`/dsa/problems/${id}`, { method: "DELETE" }),

    analyze: (id: number) =>
      request<DsaAnalysisOut>(`/dsa/problems/${id}/analyze`, { method: "POST" }),
  },
  analytics: {
    stats: () => request<AnalyticsStats>("/analytics/stats"),
  },
  settings: {
    get: () => request<UserSettings>("/settings/"),
    patch: (body: SettingsPatch) =>
      request<UserSettings>("/settings/", { method: "PATCH", body: JSON.stringify(body) }),
    voicePreviewUrl: (voiceId: string) => `${BASE}/settings/voice-preview/${voiceId}`,
  },
  pilot: {
    greeting: () => request<{ text: string }>("/pilot/greeting"),
    chat: (message: string, history: PilotTurn[]) =>
      request<PilotAgentResponse>("/pilot/agent", {
        method: "POST",
        body: JSON.stringify({ message, history }),
      }),
    /**
     * Streaming variant. Consumes a Server-Sent Events response from
     * /pilot/agent/stream and invokes the callback for each event. Returns
     * the final reply text + tool trace once the `done` event arrives.
     */
    streamChat: async (
      message: string,
      history: PilotTurn[],
      onEvent: (e: PilotStreamEvent) => void,
      signal?: AbortSignal,
    ): Promise<PilotAgentResponse> => {
      const res = await fetch(`${BASE}/pilot/agent/stream`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
        signal,
      });
      if (!res.ok || !res.body) {
        const b = await res.json().catch(() => ({}));
        throw new ApiError(
          res.status,
          "stream_error",
          b.detail || res.statusText,
        );
      }
      _maybeDispatchGamify(res);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalReply = "";
      let finalTrace: PilotToolTrace[] = [];
      let finalOutcome = "ok";
      let tokensIn = 0;
      let tokensOut = 0;
      let steps = 0;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        // SSE splits messages with \n\n.
        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          const dataLine = raw
            .split("\n")
            .find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          const payload = dataLine.slice(5).trim();
          if (!payload) continue;
          try {
            const evt = JSON.parse(payload) as PilotStreamEvent;
            onEvent(evt);
            if (evt.type === "done") {
              finalReply = evt.reply;
              finalOutcome = evt.outcome;
              tokensIn = evt.tokens_in;
              tokensOut = evt.tokens_out;
              steps = evt.steps;
            } else if (evt.type === "trace") {
              finalTrace = evt.trace;
            } else if (evt.type === "error") {
              throw new ApiError(500, "stream_error", evt.message);
            }
          } catch (err) {
            if (err instanceof ApiError) throw err;
            // Skip malformed lines silently.
          }
        }
      }
      return {
        reply: finalReply,
        tool_trace: finalTrace,
        tokens_in: tokensIn,
        tokens_out: tokensOut,
        steps,
        outcome: finalOutcome,
      };
    },
    history: (limit = 50) =>
      request<{ turns: PilotHistoryTurn[] }>(`/pilot/history?limit=${limit}`),
    stt: async (audio: Blob, filename: string): Promise<{ text: string }> => {
      const form = new FormData();
      form.append("audio", audio, filename);
      const res = await fetch(`${BASE}/pilot/stt`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new ApiError(res.status, "stt_error", b.detail || res.statusText);
      }
      _maybeDispatchGamify(res);
      return res.json();
    },
    tts: async (text: string): Promise<Blob> => {
      const res = await fetch(`${BASE}/pilot/tts`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new ApiError(res.status, "tts_error", b.detail || res.statusText);
      }
      return res.blob();
    },
  },
};

export type PilotTurn = { role: "user" | "assistant"; content: string };
export type PilotChatResponse = {
  reply: string;
  tokens_in: number;
  tokens_out: number;
};
export type PilotToolTrace = {
  name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
  latency_ms: number;
};
export type PilotAgentResponse = {
  reply: string;
  tool_trace: PilotToolTrace[];
  tokens_in: number;
  tokens_out: number;
  steps: number;
  outcome: string;
};

export type PilotHistoryTurn = {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  tokens_in: number;
  tokens_out: number;
  tool_calls: PilotToolTrace[] | null;
  created_at: string;
};

export type PilotStreamEvent =
  | { type: "trace"; trace: PilotToolTrace[] }
  | { type: "delta"; text: string }
  | {
      type: "done";
      reply: string;
      outcome: string;
      tokens_in: number;
      tokens_out: number;
      steps: number;
    }
  | { type: "error"; message: string };
