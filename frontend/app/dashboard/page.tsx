"use client";

import { BarChart2, LayoutDashboard } from "lucide-react";
import { useState } from "react";

import { useMe } from "@/hooks/useMe";
import { useDashboardStats } from "@/hooks/useDashboard";
import { AppShell } from "@/components/layout/AppShell";
import { AnalyticsPanel } from "@/components/analytics/AnalyticsPanel";
import { DailyBoard } from "@/components/dashboard/DailyBoard";
import { FollowUpsCard } from "@/components/dashboard/FollowUpsCard";
import { PipelineCard } from "@/components/dashboard/PipelineCard";
import { RankCard } from "@/components/dashboard/RankCard";
import { StatStrip } from "@/components/dashboard/StatStrip";
import { StudySummaryCard } from "@/components/dashboard/StudySummaryCard";
import { WeeklyGoals } from "@/components/dashboard/WeeklyGoals";
import { XpWeekChart } from "@/components/dashboard/XpWeekChart";

type Tab = "overview" | "analytics";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function todayStr(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview",   label: "Overview",  icon: LayoutDashboard },
  { id: "analytics",  label: "Analytics", icon: BarChart2       },
];

export default function DashboardPage() {
  const { data: me } = useMe();
  const stats = useDashboardStats();
  const s = stats.data;
  const [tab, setTab] = useState<Tab>("overview");

  const firstName = me?.display_name?.split(" ")[0] ?? "there";

  return (
    <AppShell>
      <main className="flex-1 bg-[var(--color-bg)]">
        <div className="max-w-[1100px] w-full mx-auto px-5 pt-7 pb-14">

          <header className="mb-5 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div>
              <h1 className="text-[22px] font-bold tracking-tight text-[var(--color-text)]">
                {greeting()}, {firstName}
              </h1>
              <p className="text-[12.5px] text-[var(--color-text-3)] mt-1">{todayStr()}</p>
            </div>

            {/* Tab switcher */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] self-start sm:self-auto">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTab(id)}
                  className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${
                    tab === id
                      ? "bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm ring-1 ring-[var(--color-border)]"
                      : "text-[var(--color-text-3)] hover:text-[var(--color-text)]"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </header>

          {/* ── OVERVIEW TAB ─────────────────────────────────────── */}
          {tab === "overview" && (
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-5 items-start">
              {/* Main column */}
              <div className="flex flex-col gap-4">
                {s ? (
                  <StatStrip stats={s} />
                ) : (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-24 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl animate-pulse"
                      />
                    ))}
                  </div>
                )}
                {s && <PipelineCard stats={s} />}
                <DailyBoard />
                <StudySummaryCard />
                <FollowUpsCard />
              </div>

              {/* Sidebar */}
              <div className="flex flex-col gap-4">
                <RankCard />
                <WeeklyGoals />
                <XpWeekChart />
              </div>
            </div>
          )}

          {/* ── ANALYTICS TAB ────────────────────────────────────── */}
          {tab === "analytics" && (
            <div>
              <div className="mb-5">
                <p className="text-[13.5px] text-[var(--color-text-3)]">
                  Your job search funnel at a glance
                </p>
              </div>
              <AnalyticsPanel />
            </div>
          )}

        </div>
      </main>
    </AppShell>
  );
}
