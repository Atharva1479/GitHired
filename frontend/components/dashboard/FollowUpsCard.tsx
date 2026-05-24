"use client";

import Link from "next/link";
import { useTodayNudges } from "@/hooks/useNudges";
import type { Nudge, NudgeSeverity } from "@/lib/nudges";

function urgencyLabel(nudge: Nudge): { text: string; color: string } {
  if (nudge.severity === "overdue")
    return { text: "Overdue", color: "#c06060" };
  if (nudge.severity === "due")
    return { text: "Due today", color: "#c89040" };
  return { text: "Heads up", color: "var(--color-text-3)" };
}

function dotColorForSeverity(severity: NudgeSeverity): string {
  if (severity === "overdue") return "#c06060";
  if (severity === "due") return "#c89040";
  return "var(--color-border)";
}

const NUDGE_TYPE_LABEL: Record<string, string> = {
  application_followup: "Application follow-up",
  application_stale: "Application went stale",
  application_interview_stale: "Interview went stale",
  apply_more: "Time to apply more",
  referral_check: "Check in with referral",
  referral_unaccepted: "Referral not yet accepted",
  referral_ask: "Ask for a referral",
  referral_followup: "Referral follow-up",
};

export function FollowUpsCard() {
  const { data: nudges, isLoading } = useTodayNudges();

  if (isLoading) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 animate-pulse h-32" />
    );
  }

  const sorted = [...(nudges ?? [])].sort((a, b) => {
    const order: Record<string, number> = { overdue: 0, due: 1, info: 2 };
    return (order[a.severity] ?? 2) - (order[b.severity] ?? 2);
  });

  const visible = sorted.slice(0, 3);
  if (visible.length === 0) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          Upcoming Follow-ups
        </span>
        <Link
          href="/nudges"
          className="text-[11.5px] text-[var(--color-text-3)] hover:text-[var(--color-text-2)] transition-colors"
        >
          All nudges →
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {visible.map((n) => {
          const { text, color } = urgencyLabel(n);
          return (
            <div
              key={n.id}
              className="flex items-center gap-2.5 bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl px-3 py-2.5"
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: dotColorForSeverity(n.severity) }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-medium text-[var(--color-text-2)] truncate">
                  {n.message}
                </div>
                <div className="text-[10.5px] text-[var(--color-text-3)] mt-0.5 truncate">
                  {NUDGE_TYPE_LABEL[n.type] ?? n.type}
                </div>
              </div>
              <span className="text-[10.5px] font-semibold shrink-0" style={{ color }}>
                {text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
