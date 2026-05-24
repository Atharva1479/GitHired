"use client";

import { BookOpenCheck, RefreshCw, Star } from "lucide-react";
import Link from "next/link";

import { useStudyPlan, useStudyProgress } from "@/hooks/useStudy";

import { StudyProgressBar } from "./StudyProgressBar";

export function StudyCard() {
  const { data: plan } = useStudyPlan();
  const { data: progress, isLoading } = useStudyProgress();

  // Hide card completely if user has no study plan yet.
  if (!plan || plan.sections.length === 0) return null;

  if (isLoading || !progress) {
    return (
      <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-4 shadow-sm animate-pulse h-28" />
    );
  }

  const completed = progress.done + progress.mastered;
  const pct =
    progress.total_topics > 0
      ? Math.round((completed / progress.total_topics) * 100)
      : 0;

  return (
    <Link href="/study" className="block group">
      <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] hover:ring-indigo-400 p-4 shadow-sm hover:shadow-md transition-all">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-500/10">
              <BookOpenCheck className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="text-[12px] font-semibold text-[var(--color-text-2)]">
              Study Plan
            </span>
          </div>
          <span className="text-[13px] font-bold text-indigo-400 tabular-nums">
            {pct}%
          </span>
        </div>

        <StudyProgressBar done={completed} total={progress.total_topics} />

        <div className="flex items-center gap-1.5 mt-2 flex-wrap text-[11.5px] text-[var(--color-text-3)]">
          <span className="tabular-nums">{completed}/{progress.total_topics} topics</span>
          {progress.mastered > 0 && (
            <>
              <span className="text-[var(--color-border)]">·</span>
              <span className="inline-flex items-center gap-0.5 text-amber-400">
                <Star className="w-3 h-3" />
                {progress.mastered} mastered
              </span>
            </>
          )}
          {progress.due_for_review > 0 && (
            <>
              <span className="text-[var(--color-border)]">·</span>
              <span className="inline-flex items-center gap-0.5 font-medium text-amber-400 bg-amber-500/10 ring-1 ring-amber-500/20 px-1.5 py-0.5 rounded-full">
                <RefreshCw className="w-2.5 h-2.5" />
                {progress.due_for_review} due
              </span>
            </>
          )}
          {progress.revisions_this_week > 0 && (
            <>
              <span className="text-[var(--color-border)]">·</span>
              <span className="text-emerald-400 tabular-nums">{progress.revisions_this_week} this week</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}
