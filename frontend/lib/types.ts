export type Status =
  | "Applied"
  | "Screening"
  | "Interview"
  | "Offer"
  | "Rejected"
  | "Ghosted";

export type Source =
  | "LinkedIn"
  | "Naukri"
  | "Referral"
  | "CompanySite"
  | "Other";

export const STATUSES: Status[] = [
  "Applied",
  "Screening",
  "Interview",
  "Offer",
  "Rejected",
  "Ghosted",
];

export const SOURCES: Source[] = [
  "LinkedIn",
  "Naukri",
  "Referral",
  "CompanySite",
  "Other",
];

export const STATUS_META: Record<
  Status,
  {
    label: string;
    chip: string;       // pill background + text
    dot: string;        // small colored dot
    columnAccent: string; // top-of-column thin bar
  }
> = {
  Applied: {
    label: "Applied",
    chip: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
    dot: "bg-blue-500",
    columnAccent: "bg-blue-500",
  },
  Screening: {
    label: "Screening",
    chip: "bg-violet-50 text-violet-700 ring-1 ring-violet-200",
    dot: "bg-violet-500",
    columnAccent: "bg-violet-500",
  },
  Interview: {
    label: "Interview",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    dot: "bg-amber-500",
    columnAccent: "bg-amber-500",
  },
  Offer: {
    label: "Offer",
    chip: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
    dot: "bg-emerald-500",
    columnAccent: "bg-emerald-500",
  },
  Rejected: {
    label: "Rejected",
    chip: "bg-red-50 text-red-700 ring-1 ring-red-200",
    dot: "bg-red-500",
    columnAccent: "bg-red-400",
  },
  Ghosted: {
    label: "Ghosted",
    chip: "bg-gray-100 text-gray-700 ring-1 ring-gray-300",
    dot: "bg-gray-400",
    columnAccent: "bg-gray-400",
  },
};

const COMPANY_COLORS = [
  "bg-rose-100 text-rose-700",
  "bg-orange-100 text-orange-700",
  "bg-amber-100 text-amber-700",
  "bg-lime-100 text-lime-700",
  "bg-emerald-100 text-emerald-700",
  "bg-teal-100 text-teal-700",
  "bg-sky-100 text-sky-700",
  "bg-indigo-100 text-indigo-700",
  "bg-violet-100 text-violet-700",
  "bg-pink-100 text-pink-700",
];

export function companyAvatarClass(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return COMPANY_COLORS[Math.abs(hash) % COMPANY_COLORS.length];
}

export type FileKind = "jd" | "resume" | "cover_letter";

export const FILE_KIND_LABEL: Record<FileKind, string> = {
  jd: "Job description",
  resume: "Resume",
  cover_letter: "Cover letter",
};

export type Application = {
  id: number;
  company: string;
  role: string;
  source: Source;
  status: Status;
  applied_date: string;
  last_updated: string;
  jd_url: string | null;
  salary_discussed: string | null;
  contact_name: string | null;
  contact_linkedin: string | null;
  fit_score: number | null;
  notes: string | null;
  follow_up_count: number;
  last_followed_up_at: string | null;
  created_at: string;
  jd_text: string | null;
  jd_file_name: string | null;
  resume_file_name: string | null;
  cover_letter_file_name: string | null;
};

export type ApplicationCreate = {
  company: string;
  role: string;
  source: Source;
  applied_date: string;
  jd_url?: string | null;
  jd_text?: string | null;
  contact_name?: string | null;
  contact_linkedin?: string | null;
  fit_score?: number | null;
  notes?: string | null;
  salary_discussed?: string | null;
};

export type ApplicationUpdate = Partial<{
  company: string;
  role: string;
  source: Source;
  applied_date: string;
  status: Status;
  notes: string | null;
  fit_score: number | null;
  salary_discussed: string | null;
  contact_name: string | null;
  contact_linkedin: string | null;
  jd_url: string | null;
  jd_text: string | null;
}>;

// ───────────────────────  Study tracker (M10)  ───────────────────────

export type StudyKind = "learn" | "revise";
export type StudyStatus = "todo" | "in_progress" | "done" | "mastered";

export const STUDY_KINDS: StudyKind[] = ["learn", "revise"];
export const STUDY_STATUSES: StudyStatus[] = [
  "todo",
  "in_progress",
  "done",
  "mastered",
];

export type StudySection = {
  id: number;
  name: string;
  icon: string | null;
  position: number;
  created_at: string;
  last_updated: string;
};

export type StudySubsection = {
  id: number;
  section_id: number;
  name: string;
  position: number;
  created_at: string;
  last_updated: string;
};

export type StudyTopic = {
  id: number;
  subsection_id: number;
  title: string;
  notes: string | null;
  kind: StudyKind;
  status: StudyStatus;
  tags: string[];
  revision_count: number;
  last_revised_at: string | null;
  position: number;
  created_at: string;
  last_updated: string;
};

export type StudyPlanSubsection = StudySubsection & {
  topics: StudyTopic[];
};

export type StudyPlanSection = StudySection & {
  subsections: StudyPlanSubsection[];
};

export type StudyPlan = {
  sections: StudyPlanSection[];
};

export type StudyProgress = {
  total_topics: number;
  todo: number;
  in_progress: number;
  done: number;
  mastered: number;
  revisions_this_week: number;
  due_for_review: number;
};

export type StudySectionCreate = {
  name: string;
  icon?: string | null;
  position?: number;
};

export type StudySectionUpdate = Partial<{
  name: string;
  icon: string | null;
  position: number;
}>;

export type StudySubsectionCreate = {
  name: string;
  position?: number;
};

export type StudySubsectionUpdate = Partial<{
  name: string;
  position: number;
  section_id: number;
}>;

export type StudyTopicCreate = {
  title: string;
  notes?: string | null;
  kind?: StudyKind;
  tags?: string[];
  position?: number;
};

export type StudyTopicUpdate = Partial<{
  title: string;
  notes: string | null;
  kind: StudyKind;
  status: StudyStatus;
  tags: string[];
  position: number;
  subsection_id: number;
}>;

export type StudyReviseResponse = {
  topic: StudyTopic;
  revision_count: number;
  new_status: StudyStatus;
};

// ── M10 Phase 4 — AI generation previews ────────────────────────────

export type StudyAITopicPreview = {
  title: string;
  notes?: string | null;
};

export type StudyAISubsectionPreview = {
  name: string;
  topics: StudyAITopicPreview[];
};

export type StudyAISectionPreview = {
  name: string;
  subsections: StudyAISubsectionPreview[];
};

export type StudyGenerateRequest = {
  role: string;
  target_companies?: string[] | null;
  existing_sections?: string[] | null;
};

export type StudyGenerateResponse = {
  sections: StudyAISectionPreview[];
};

export type StudyGenerateTopicsRequest = {
  count?: number;
  hint?: string | null;
};

export type StudyGenerateTopicsResponse = {
  topics: StudyAITopicPreview[];
};

// ── DSA Progress Tracker ──────────────────────────────────────────────────────

export type DsaDifficulty = "easy" | "medium" | "hard";

export interface DsaAnalysisOut {
  id: number;
  problem_id: number;
  user_id: number;
  time_complexity: string;
  space_complexity: string;
  approach_summary: string;
  feedback: string;
  optimized_solution: string;
  optimized_explanation: string;
  dry_run_explanation: string;
  model: string;
  created_at: string;
}

export interface DsaProblemOut {
  id: number;
  user_id: number;
  topic: string;
  difficulty: DsaDifficulty;
  title: string;
  source_url: string | null;
  description: string | null;
  user_solution: string | null;
  solved_at: string;
  created_at: string;
  last_updated: string;
  deleted_at: string | null;
  analysis: DsaAnalysisOut | null;
}

export interface DsaProblemCreate {
  topic: string;
  difficulty: DsaDifficulty;
  title: string;
  source_url?: string;
  description?: string;
  user_solution?: string;
}

export interface DsaProblemUpdate {
  topic?: string;
  difficulty?: DsaDifficulty;
  title?: string;
  source_url?: string | null;
  description?: string | null;
  user_solution?: string | null;
}

export interface DsaTopicStats {
  topic: string;
  count: number;
  analyzed: number;
}

export interface DsaStatsOut {
  total_solved: number;
  by_difficulty: Record<string, number>;
  topics: DsaTopicStats[];
  analyzed_count: number;
  streak_days: number;
}
