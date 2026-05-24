"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAnalyticsStats } from "@/hooks/useAnalytics";

const SOURCE_COLORS: Record<string, string> = {
  LinkedIn:    "#0a66c2",
  Naukri:      "#ff6600",
  Referral:    "#10b981",
  CompanySite: "#6366f1",
  Other:       "#94a3b8",
};

const STATUS_COLORS: Record<string, string> = {
  Applied:   "#6366f1",
  Screening: "#f59e0b",
  Interview: "#3b82f6",
  Offer:     "#10b981",
  Rejected:  "#f43f5e",
  Ghosted:   "#94a3b8",
};

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <p className="text-[11.5px] text-[var(--color-text-3)] uppercase tracking-wide mb-1">{label}</p>
      <p className="text-[28px] font-bold text-[var(--color-text)] leading-none">{value}</p>
      {sub && <p className="text-[12px] text-[var(--color-text-3)] mt-1">{sub}</p>}
    </div>
  );
}

export function AnalyticsPanel() {
  const { data, isLoading, error } = useAnalyticsStats();

  if (isLoading) {
    return (
      <div className="min-h-[30vh] grid place-items-center">
        <div className="h-8 w-8 rounded-full border-2 border-[var(--color-border)] border-t-indigo-600 animate-spin" />
      </div>
    );
  }
  if (error) return <p className="text-rose-500 text-sm">Failed to load analytics.</p>;
  if (!data) return <p className="text-sm text-[var(--color-text-3)]">No analytics data available.</p>;

  return (
    <div className="space-y-6">
      {/* Funnel stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Applied"       value={data.funnel.applied}                                   />
        <StatCard label="Screened"      value={data.funnel.screened}                                  />
        <StatCard label="Interviewed"   value={data.funnel.interviewed}                               />
        <StatCard label="Offers"        value={data.funnel.offered}                                   />
        <StatCard label="Response Rate" value={`${data.funnel.response_rate}%`} sub="of closed apps"  />
        <StatCard label="Offer Rate"    value={`${data.funnel.offer_rate}%`}    sub="of total applied" />
      </div>

      {/* Weekly trend + status breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-4">
            Applications — Last 8 Weeks
          </h3>
          {data.weekly_trend.length === 0 ? (
            <p className="text-[13px] text-[var(--color-text-3)]">No data yet.</p>
          ) : (
            <div role="img" aria-label="Weekly applications bar chart">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.weekly_trend}>
                  <XAxis
                    dataKey="week_start"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v: unknown) => {
                      const [y, m, d] = String(v).split("-").map(Number);
                      return new Date(y, m - 1, d).toLocaleDateString("en", { month: "short", day: "numeric" });
                    }}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    labelFormatter={(v: unknown) => {
                      const [y, m, d] = String(v).split("-").map(Number);
                      return `Week of ${new Date(y, m - 1, d).toLocaleDateString("en", { month: "short", day: "numeric" })}`;
                    }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-4">
            Status Breakdown
          </h3>
          {data.by_status.length === 0 ? (
            <p className="text-[13px] text-[var(--color-text-3)]">No data yet.</p>
          ) : (
            <div role="img" aria-label="Application status donut chart" className="flex items-center gap-4">
              <div style={{ width: 160, height: 160, flexShrink: 0 }}>
                <PieChart width={160} height={160}>
                  <Pie data={data.by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" innerRadius={40} outerRadius={70}>
                    {data.by_status.map((entry) => (
                      <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "#94a3b8"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </div>
              <ul className="space-y-2 flex-1">
                {data.by_status.map((s) => (
                  <li key={s.status} className="flex items-center gap-2 text-[13px]">
                    <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ background: STATUS_COLORS[s.status] ?? "#94a3b8" }} />
                    <span className="text-[var(--color-text-2)]">{s.status}</span>
                    <span className="ml-auto font-semibold text-[var(--color-text)]">{s.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Source breakdown */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <h3 className="text-[14px] font-semibold text-[var(--color-text)] mb-4">
          Applications by Source
        </h3>
        {data.by_source.length === 0 ? (
          <p className="text-[13px] text-[var(--color-text-3)]">No data yet.</p>
        ) : (
          <div className="space-y-3">
            {data.by_source.map((s) => {
              const pct = data.funnel.applied > 0 ? Math.round((s.count / data.funnel.applied) * 100) : 0;
              return (
                <div key={s.source}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ background: SOURCE_COLORS[s.source] ?? "#94a3b8" }} />
                      <span className="text-[13px] text-[var(--color-text-2)]">{s.source}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[13px]">
                      <span className="text-[var(--color-text-3)]">{s.count} apps</span>
                      <span className="text-[var(--color-text-3)]">{s.response_rate}% response</span>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--color-surface-2)]">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, background: SOURCE_COLORS[s.source] ?? "#94a3b8" }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
