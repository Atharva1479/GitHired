import Link from "next/link";
import type { DashboardStats } from "@/lib/dashboard";

const STAGE_COLOR: Record<string, string> = {
  applied:   "text-[var(--color-text)]",
  screening: "text-[#c89040]",
  interview: "text-[#9b7ee8]",
  offer:     "text-[#3db87a]",
  rejected:  "text-[var(--color-text-3)]",
};

export function PipelineCard({ stats }: { stats: DashboardStats }) {
  const { applications: apps } = stats;

  const active = apps.in_progress;
  const rejected = Math.max(0, apps.total - apps.applied - active - apps.offers);
  const interview = Math.max(0, active - 1);
  const screening = Math.max(0, active - interview);

  const stages = [
    { key: "applied",   label: "Applied",   count: apps.applied },
    { key: "screening", label: "Screening",  count: screening },
    { key: "interview", label: "Interview",  count: interview },
    { key: "offer",     label: "Offer",      count: apps.offers },
    { key: "rejected",  label: "Rejected",   count: rejected },
  ];

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          Application Pipeline
        </span>
        <Link
          href="/applications"
          className="text-[11.5px] text-[var(--color-text-3)] hover:text-[var(--color-text-2)] transition-colors"
        >
          View all →
        </Link>
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {stages.map((s) => (
          <div
            key={s.key}
            className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-lg p-2.5 text-center"
          >
            <div className={`text-[20px] font-bold tracking-tight leading-none ${STAGE_COLOR[s.key]}`}>
              {s.count}
            </div>
            <div className="text-[9px] font-semibold uppercase tracking-wider mt-1 text-[var(--color-text-3)]">
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
