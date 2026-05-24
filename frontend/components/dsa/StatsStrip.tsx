import type { DsaStatsOut } from "@/lib/types";

const DIFF_COLOR: Record<string, string> = {
  easy: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-400 dark:ring-emerald-500/30",
  medium: "bg-amber-50 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-400 dark:ring-amber-500/30",
  hard: "bg-rose-50 text-rose-700 ring-1 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-400 dark:ring-rose-500/30",
};

export function DsaStatsStrip({ stats }: { stats: DsaStatsOut }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <StatCard label="Problems Solved" value={stats.total_solved} />
      <StatCard label="AI Analyzed" value={stats.analyzed_count} />
      <StatCard label="Topics" value={stats.topics.length} />
      <StatCard label="Day Streak" value={stats.streak_days} suffix="🔥" />

      <div className="col-span-full flex flex-wrap gap-2">
        {(["easy", "medium", "hard"] as const).map((d) => (
          <span
            key={d}
            className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium capitalize ${DIFF_COLOR[d]}`}
          >
            {d}
            <span className="font-bold">{stats.by_difficulty[d] ?? 0}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number;
  suffix?: string;
}) {
  return (
    <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-4 shadow-sm">
      <p className="text-[12px] text-[var(--color-text-3)] mb-1">{label}</p>
      <p className="text-[24px] font-bold text-[var(--color-text)] leading-none">
        {value}
        {suffix ? <span className="ml-1 text-xl">{suffix}</span> : null}
      </p>
    </div>
  );
}
