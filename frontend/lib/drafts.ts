export type DraftEntityType = "application" | "referral";
export type DraftType =
  | "followup_email"
  | "referral_ask"
  | "referral_followup"
  | "weekly_summary";

export type Draft = {
  id: number;
  entity_type: DraftEntityType;
  entity_id: number;
  draft_type: DraftType;
  content: string;
  model: string;
  cached: boolean;
  fallback: boolean;
  created_at: string;
};

export const DRAFT_TITLE: Record<DraftType, string> = {
  followup_email: "Follow-up email",
  referral_ask: "Referral ask",
  referral_followup: "Gentle follow-up",
  weekly_summary: "Weekly summary",
};

export const DRAFT_SUBTITLE: Record<DraftType, string> = {
  followup_email:
    "A polite nudge to the hiring team about your application status.",
  referral_ask:
    "A warm LinkedIn message asking for a referral at their company.",
  referral_followup:
    "A short, no-guilt-trip ping after silence on your referral ask.",
  weekly_summary: "Recap of the week's job-search activity.",
};
