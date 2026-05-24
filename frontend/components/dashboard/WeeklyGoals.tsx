"use client";

import { useDashboardStats } from "@/hooks/useDashboard";
import { useStudyProgress } from "@/hooks/useStudy";

const TARGETS = { apps: 5, referrals: 3, study: 5 };

function GoalBar({
  label,
  value,
  target,
  color,
}: {
  label: string;
  value: number;
  target: number;
  color: string;
}) {
  const pct = Math.min(100, Math.round((value / target) * 100));
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between mb-1.5">
        <span className="text-[12px] text-[var(--color-text-3)]">{label}</span>
        <span className="text-[12px] font-semibold text-[var(--color-text-2)]">
          {value} / {target}
        </span>
      </div>
      <div className="h-[3px] bg-[var(--color-surface-2)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-[width] duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export function WeeklyGoals() {
  const stats = useDashboardStats();
  const study = useStudyProgress();

  const appsThisWeek = stats.data?.applications.total ?? 0;
  const referralsThisWeek = stats.data?.referrals.total ?? 0;
  const studyThisWeek = study.data?.revisions_this_week ?? 0;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          Weekly Goals
        </span>
        <span className="text-[10px] text-[var(--color-text-3)]">Mon–Sun</span>
      </div>
      <GoalBar label="Applications sent" value={appsThisWeek} target={TARGETS.apps} color="#5a90d8" />
      <GoalBar label="Referral outreach" value={referralsThisWeek} target={TARGETS.referrals} color="#8b6de0" />
      <GoalBar label="Study topics" value={studyThisWeek} target={TARGETS.study} color="#3daa7a" />
    </div>
  );
}
