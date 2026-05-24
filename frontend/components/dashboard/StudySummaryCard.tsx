"use client";

import Link from "next/link";
import { useStudyPlan, useStudyProgress } from "@/hooks/useStudy";

export function StudySummaryCard() {
  const { data: plan } = useStudyPlan();
  const { data: progress, isLoading } = useStudyProgress();

  if (!plan || plan.sections.length === 0) return null;

  if (isLoading || !progress) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 animate-pulse h-24" />
    );
  }

  const completed = progress.done + progress.mastered;
  const pct = progress.total_topics > 0
    ? Math.round((completed / progress.total_topics) * 100)
    : 0;

  return (
    <Link href="/study" className="block group">
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 hover:border-[#8b6de0]/50 transition-colors">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
            Study Progress
          </span>
          <span className="text-[11.5px] text-[var(--color-text-3)] group-hover:text-[var(--color-text-2)] transition-colors">
            Open →
          </span>
        </div>
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-[26px] font-bold tracking-tight text-[#9b7ee8] leading-none">
            {pct}%
          </span>
          <span className="text-[12px] text-[var(--color-text-3)]">
            {completed} of {progress.total_topics} topics complete
          </span>
        </div>
        <div className="h-1 bg-[var(--color-surface-2)] rounded-full overflow-hidden mb-2">
          <div
            className="h-full rounded-full transition-[width] duration-700"
            style={{ width: `${pct}%`, background: "linear-gradient(90deg, #8b6de0, #a78bfa)" }}
          />
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {progress.due_for_review > 0 && (
            <span className="text-[10.5px] font-semibold text-[#c89040] bg-[#c89040]/10 border border-[#c89040]/20 rounded-full px-2 py-0.5">
              ⟳ {progress.due_for_review} due for review
            </span>
          )}
          {progress.mastered > 0 && (
            <span className="text-[10.5px] text-[#9080e0]">
              ★ {progress.mastered} mastered
            </span>
          )}
          {progress.revisions_this_week > 0 && (
            <span className="text-[10.5px] text-[#3daa7a]">
              ↑ {progress.revisions_this_week} revision{progress.revisions_this_week === 1 ? "" : "s"} this week
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
