/**
 * Mapping from voice-agent tool names → React Query keys to invalidate.
 *
 * Why this exists: the voice agent writes to the DB through the
 * backend tool registry (add_application, delete_referral, etc.).
 * The frontend has React Query caches holding the *previous* state
 * of those rows. Without explicit invalidation the lists are stale
 * until the user reloads — a confusing bug ("I told the agent to add
 * Stripe but I don't see it!").
 *
 * Keep the keys in sync with the ones declared in /hooks. If you add
 * a new write tool to backend/services/pilot_tools.py, add it here too.
 */
import type { PilotToolTrace } from "@/lib/api";

type QueryKey = readonly unknown[];

// Pure read tools — no cache touched.
const _READ_ONLY = new Set<string>([
  "get_profile",
  "get_stats",
  "get_xp_state",
  "list_applications",
  "get_application",
  "list_referrals",
  "get_referral",
  "list_recent_activity",
  "list_pending_nudges",
  "list_drafts",
  "list_achievements",
  // M10 study read tools — voice may add these later; pre-registering
  // keeps unknown-tool warnings quiet when Phase 5 ships them.
  "list_study_plan",
  "get_study_progress",
  "list_due_topics",
  // DSA tracker read tool — read-only, never mutates.
  "get_dsa_progress",
]);

const APPLICATIONS_LIST: QueryKey = ["applications"];
const REFERRALS_LIST: QueryKey = ["referrals"];
const DASHBOARD_STATS: QueryKey = ["dashboard", "stats"];
const DASHBOARD_ACTIVITY: QueryKey = ["dashboard", "activity"];
const GAMIFY_STATE: QueryKey = ["gamify", "state"];
const NUDGES_LIST: QueryKey = ["nudges"];
const NUDGES_TODAY: QueryKey = ["nudges", "today"];
const PILOT_HISTORY: QueryKey = ["pilot", "history"];
const STUDY_PLAN: QueryKey = ["study", "plan"];
const STUDY_PROGRESS: QueryKey = ["study", "progress"];

function applicationOneKey(id: number): QueryKey {
  return ["application", id];
}
function referralOneKey(id: number): QueryKey {
  return ["referral", id];
}
function referralLinkedKey(id: number): QueryKey {
  return ["referral", id, "applications"];
}

/**
 * Inspect a single tool-trace entry and return the keys it invalidates.
 * Empty array means "no cache touched" (read tool, refused write, or
 * a needs_confirmation response that didn't actually mutate yet).
 */
export function keysForToolEntry(entry: PilotToolTrace): QueryKey[] {
  const name = entry.name;
  if (_READ_ONLY.has(name)) return [];

  // A needs_confirmation result hasn't mutated anything yet — the user
  // still has to say "yes". Skip; the second call (with confirm_token)
  // will land here as its own trace entry and invalidate then.
  const result = entry.result || {};
  if (result.needs_confirmation === true) return [];

  // An errored tool didn't change the DB either.
  if ("error" in result) return [];

  const args = entry.args || {};
  const out: QueryKey[] = [PILOT_HISTORY]; // every successful write shows up in history

  switch (name) {
    case "add_application":
      return [
        ...out,
        APPLICATIONS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
    case "update_application":
    case "move_application_status":
    case "add_note_to_application": {
      const keys: QueryKey[] = [
        ...out,
        APPLICATIONS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
      const id = numberFromArgs(args.id);
      if (id != null) keys.push(applicationOneKey(id));
      return keys;
    }
    case "delete_application": {
      const keys: QueryKey[] = [
        ...out,
        APPLICATIONS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
      const id = numberFromArgs(args.id);
      if (id != null) keys.push(applicationOneKey(id));
      return keys;
    }
    case "add_referral":
      return [
        ...out,
        REFERRALS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
    case "update_referral":
    case "mark_referral_accepted":
    case "mark_referral_sent":
    case "mark_referral_replied": {
      const keys: QueryKey[] = [
        ...out,
        REFERRALS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
      const id = numberFromArgs(args.id);
      if (id != null) keys.push(referralOneKey(id));
      return keys;
    }
    case "delete_referral": {
      const keys: QueryKey[] = [
        ...out,
        REFERRALS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
      ];
      const id = numberFromArgs(args.id);
      if (id != null) keys.push(referralOneKey(id));
      return keys;
    }
    case "link_referral_to_application":
    case "unlink_referral_from_application": {
      const keys: QueryKey[] = [...out, APPLICATIONS_LIST, REFERRALS_LIST];
      const refId = numberFromArgs(args.referral_id);
      const appId = numberFromArgs(args.application_id);
      if (refId != null) {
        keys.push(referralOneKey(refId), referralLinkedKey(refId));
      }
      if (appId != null) keys.push(applicationOneKey(appId));
      return keys;
    }
    case "generate_followup_draft":
    case "generate_referral_ask":
      // Drafts aren't list-cached today (loaded on demand inside detail
      // panels), so just refresh the history surface so the audit log
      // shows the draft was created.
      return out;
    // ── M10 study tracker writes ────────────────────────────────────
    case "add_study_section":
    case "delete_study_section":
    case "add_study_subsection":
    case "delete_study_subsection":
    case "add_study_topic":
    case "delete_study_topic":
    case "update_study_topic":
    case "generate_study_plan":
    case "generate_topics_for_subsection":
      // Any change to the study tree refreshes the whole plan + progress
      // (the tree is fetched as one tree, no point being finer-grained).
      return [...out, STUDY_PLAN, STUDY_PROGRESS, GAMIFY_STATE];
    case "mark_topic_revised":
    case "unmark_study_topic":
      return [...out, STUDY_PLAN, STUDY_PROGRESS, GAMIFY_STATE];
    default:
      // Unknown write tool — invalidate aggressively so we don't ship
      // stale data, but log so we can map the new tool properly.
      console.warn(
        `[voice] unknown tool '${name}' in trace; invalidating broad keys`,
      );
      return [
        ...out,
        APPLICATIONS_LIST,
        REFERRALS_LIST,
        DASHBOARD_STATS,
        DASHBOARD_ACTIVITY,
        GAMIFY_STATE,
        NUDGES_LIST,
        NUDGES_TODAY,
      ];
  }
}

/**
 * Collect the de-duplicated set of query keys for an entire trace.
 * Returns them as JSON-serialised strings → original arrays so the
 * caller can iterate without invalidating the same key multiple times.
 */
export function keysForTrace(
  trace: readonly PilotToolTrace[],
): QueryKey[] {
  const seen = new Map<string, QueryKey>();
  for (const entry of trace) {
    for (const key of keysForToolEntry(entry)) {
      const hash = JSON.stringify(key);
      if (!seen.has(hash)) seen.set(hash, key);
    }
  }
  return [...seen.values()];
}

function numberFromArgs(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim()) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}
