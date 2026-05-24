export type NudgeType =
  | "application_followup"
  | "application_stale"
  | "application_interview_stale"
  | "apply_more"
  | "referral_check"
  | "referral_unaccepted"
  | "referral_ask"
  | "referral_followup";

export type NudgeReferenceType = "application" | "referral" | "user";
export type NudgeSeverity = "info" | "due" | "overdue";

export type Nudge = {
  id: number;
  type: NudgeType;
  reference_type: NudgeReferenceType;
  reference_id: number | null;
  severity: NudgeSeverity;
  message: string;
  fired_on_date: string;
  read_at: string | null;
  acted_at: string | null;
  snoozed_until: string | null;
  created_at: string;
};

export const SEVERITY_META: Record<
  NudgeSeverity,
  { label: string; chip: string; ring: string; bar: string }
> = {
  overdue: {
    label: "Overdue",
    chip: "bg-red-50 text-red-700 ring-1 ring-red-200",
    ring: "ring-red-200",
    bar: "bg-red-500",
  },
  due: {
    label: "Due",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    ring: "ring-amber-200",
    bar: "bg-amber-500",
  },
  info: {
    label: "Heads up",
    chip: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
    ring: "ring-blue-200",
    bar: "bg-blue-400",
  },
};
