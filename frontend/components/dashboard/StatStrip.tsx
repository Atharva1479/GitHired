import Link from "next/link";
import type { DashboardStats } from "@/lib/dashboard";

const DOT_COLOR = {
  blue:   "bg-[#5a90d8]",
  green:  "bg-[#3daa7a]",
  violet: "bg-[#8b6de0]",
  orange: "bg-[#c0783a]",
} as const;

type DotColor = keyof typeof DOT_COLOR;

function StatCard({
  label,
  color,
  value,
  hint,
  hintDanger,
  href,
}: {
  label: string;
  color: DotColor;
  value: string | number;
  hint: string;
  hintDanger?: boolean;
  href?: string;
}) {
  const body = (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4 hover:border-[var(--color-border-2)] transition-colors h-full">
      <div className="flex items-center gap-1.5 mb-2">
        <span className={`w-2 h-2 rounded-full shrink-0 ${DOT_COLOR[color]}`} />
        <span className="text-[10px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          {label}
        </span>
      </div>
      <div className="text-[28px] font-bold leading-none tracking-tight text-[var(--color-text)] tabular-nums">
        {value}
      </div>
      <div
        className={`mt-1.5 text-[11px] ${
          hintDanger ? "text-[#c06060]" : "text-[var(--color-text-3)]"
        }`}
      >
        {hint}
      </div>
    </div>
  );
  return href ? <Link href={href} className="block">{body}</Link> : <div>{body}</div>;
}

export function StatStrip({ stats }: { stats: DashboardStats }) {
  const { applications: apps, referrals, nudges } = stats;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
      <StatCard
        label="Applications"
        color="blue"
        value={apps.total}
        hint={`${apps.in_progress} in progress · ${apps.response_rate}% response`}
        href="/applications"
      />
      <StatCard
        label="Response Rate"
        color="green"
        value={`${apps.response_rate}%`}
        hint={`${apps.offers} offer${apps.offers === 1 ? "" : "s"} · ${apps.in_progress} active`}
      />
      <StatCard
        label="Referrals"
        color="violet"
        value={referrals.total}
        hint={`${referrals.referred} referred · ${referrals.in_progress} in progress`}
        href="/referrals"
      />
      <StatCard
        label="Follow-ups Due"
        color="orange"
        value={nudges.today}
        hint={nudges.overdue > 0 ? `${nudges.overdue} overdue · act today` : "all caught up"}
        hintDanger={nudges.overdue > 0}
        href="/nudges"
      />
    </div>
  );
}
