"use client";

import { isToday, parseISO } from "date-fns";
import { AlertTriangle, Bell, CheckCircle2, Info, PlayCircle, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { useToast } from "@/app/providers";
import { AppShell } from "@/components/layout/AppShell";
import { NudgeCard } from "@/components/nudges/NudgeCard";
import { Button } from "@/components/ui/Button";
import {
  useAllNudges,
  useRunNudges,
  useTodayNudges,
} from "@/hooks/useNudges";
import type { Nudge, NudgeReferenceType } from "@/lib/nudges";

type Filter = "all" | "applications" | "referrals";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all",          label: "All"          },
  { id: "applications", label: "Applications" },
  { id: "referrals",    label: "Referrals"    },
];

const SEVERITY_ORDER: Record<string, number> = { overdue: 0, due: 1, info: 2 };

function filterByRef(nudges: Nudge[], filter: Filter): Nudge[] {
  if (filter === "all") return nudges;
  const ref: NudgeReferenceType = filter === "applications" ? "application" : "referral";
  return nudges.filter((n) => n.reference_type === ref);
}

function sortBySeverity(nudges: Nudge[]): Nudge[] {
  return [...nudges].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3),
  );
}

export default function NudgesPage() {
  const today = useTodayNudges();
  const all   = useAllNudges();
  const run   = useRunNudges();
  const toast = useToast();
  const [filter, setFilter] = useState<Filter>("all");

  const todayNudges = today.data ?? [];
  const allNudges   = all.data ?? [];

  // Done today = acted_at is today
  const doneToday = useMemo(
    () => allNudges.filter((n) => n.acted_at && isToday(parseISO(n.acted_at))),
    [allNudges],
  );

  // History = everything that's not in today's list and not done today
  const history = useMemo(() => {
    const todayIds = new Set(todayNudges.map((n) => n.id));
    const doneTodayIds = new Set(doneToday.map((n) => n.id));
    return allNudges.filter((n) => !todayIds.has(n.id) && !doneTodayIds.has(n.id));
  }, [todayNudges, allNudges, doneToday]);

  // Stats
  const overdueCount = todayNudges.filter((n) => n.severity === "overdue").length;
  const dueCount     = todayNudges.filter((n) => n.severity === "due").length;
  const infoCount    = todayNudges.filter((n) => n.severity === "info").length;

  // Filtered + sorted today nudges
  const filtered = sortBySeverity(filterByRef(todayNudges, filter));

  // Grouped by severity (for section headers)
  const overdue = filtered.filter((n) => n.severity === "overdue");
  const due     = filtered.filter((n) => n.severity === "due");
  const info    = filtered.filter((n) => n.severity === "info");

  async function doRun() {
    try {
      const { inserted } = await run.mutateAsync();
      toast.push(
        "success",
        inserted > 0
          ? `${inserted} new nudge${inserted > 1 ? "s" : ""}`
          : "No new nudges — you're all caught up.",
      );
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Run failed");
    }
  }

  return (
    <AppShell>
      <main className="flex-1 flex flex-col">
        <div className="max-w-3xl w-full mx-auto px-6 pt-8 pb-12 flex-1">

          {/* Header */}
          <header className="flex items-end justify-between flex-wrap gap-3 mb-5">
            <div>
              <h1 className="text-[26px] font-bold tracking-tight text-[var(--color-text)]">
                Today&apos;s actions
              </h1>
              <p className="text-[14px] text-[var(--color-text-3)] mt-1">
                Pulled from your applications + referrals — most urgent first.
              </p>
            </div>
            <Button onClick={doRun} disabled={run.isPending} variant="secondary" className="gap-2">
              <PlayCircle className="w-4 h-4" />
              {run.isPending ? "Running…" : "Run check"}
            </Button>
          </header>

          {/* Stats strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-5">
            <StatPill
              icon={<AlertTriangle className="w-4 h-4" />}
              label="Overdue"
              count={overdueCount}
              tone="red"
            />
            <StatPill
              icon={<Bell className="w-4 h-4" />}
              label="Due"
              count={dueCount}
              tone="amber"
            />
            <StatPill
              icon={<Info className="w-4 h-4" />}
              label="Heads up"
              count={infoCount}
              tone="blue"
            />
            <StatPill
              icon={<CheckCircle2 className="w-4 h-4" />}
              label="Done today"
              count={doneToday.length}
              tone="green"
            />
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-1 mb-5 p-1 w-fit rounded-xl bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)]">
            {FILTERS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setFilter(id)}
                className={`px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${
                  filter === id
                    ? "bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm ring-1 ring-[var(--color-border)]"
                    : "text-[var(--color-text-3)] hover:text-[var(--color-text)]"
                }`}
              >
                {label}
                {id !== "all" && (
                  <span className="ml-1.5 text-[11px] text-[var(--color-text-3)]">
                    {id === "applications"
                      ? filterByRef(todayNudges, "applications").length
                      : filterByRef(todayNudges, "referrals").length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Today's nudges */}
          {today.isLoading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-24 rounded-xl bg-[var(--color-surface-2)] animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyToday onRun={doRun} running={run.isPending} filter={filter} />
          ) : (
            <div className="space-y-5">
              <SeverityGroup label="Overdue" tone="red"   nudges={overdue} />
              <SeverityGroup label="Due"     tone="amber" nudges={due}     />
              <SeverityGroup label="Info"    tone="blue"  nudges={info}    />
            </div>
          )}

          {/* Done today */}
          {doneToday.length > 0 && (
            <section className="mt-10">
              <SectionHeading
                label={`Completed today — ${doneToday.length}`}
                color="text-emerald-600"
              />
              <div className="space-y-3">
                {doneToday.map((n) => (
                  <NudgeCard key={n.id} nudge={n} dimmed />
                ))}
              </div>
            </section>
          )}

          {/* History */}
          <section className="mt-10">
            <SectionHeading label="History" color="text-[var(--color-text-3)]" />
            {all.isLoading ? (
              <div className="h-16 rounded-xl bg-[var(--color-surface-2)] animate-pulse" />
            ) : history.length === 0 ? (
              <p className="text-[13px] text-[var(--color-text-3)]">No past nudges yet.</p>
            ) : (
              <div className="space-y-3">
                {history.slice(0, 50).map((n) => (
                  <NudgeCard key={n.id} nudge={n} dimmed />
                ))}
              </div>
            )}
          </section>

        </div>
      </main>
    </AppShell>
  );
}

/* ── sub-components ───────────────────────────────────────────────── */

function SeverityGroup({
  label,
  tone,
  nudges,
}: {
  label: string;
  tone: "red" | "amber" | "blue";
  nudges: Nudge[];
}) {
  if (nudges.length === 0) return null;
  const colors = {
    red:   "text-red-500",
    amber: "text-amber-500",
    blue:  "text-blue-500",
  };
  return (
    <div>
      <p className={`text-[11px] font-bold uppercase tracking-widest mb-2.5 ${colors[tone]}`}>
        {label} · {nudges.length}
      </p>
      <div className="space-y-3">
        {nudges.map((n) => (
          <NudgeCard key={n.id} nudge={n} />
        ))}
      </div>
    </div>
  );
}

function SectionHeading({ label, color }: { label: string; color: string }) {
  return (
    <h2 className={`text-[11.5px] font-semibold uppercase tracking-wide mb-3 ${color}`}>
      {label}
    </h2>
  );
}

function StatPill({
  icon,
  label,
  count,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  tone: "red" | "amber" | "blue" | "green";
}) {
  const toneMap = {
    red:   { border: "border-l-red-500",     icon: "text-red-500"     },
    amber: { border: "border-l-amber-500",   icon: "text-amber-500"   },
    blue:  { border: "border-l-blue-500",    icon: "text-blue-500"    },
    green: { border: "border-l-emerald-500", icon: "text-emerald-500" },
  };
  const t = toneMap[tone];
  return (
    <div className={`rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] border-l-4 px-4 py-3 shadow-sm ${t.border}`}>
      <div className={`flex items-center gap-1.5 mb-1.5 ${t.icon}`}>{icon}</div>
      <p className="text-[26px] font-bold tabular-nums leading-none text-[var(--color-text)]">{count}</p>
      <p className="text-[11.5px] mt-1 text-[var(--color-text-3)]">{label}</p>
    </div>
  );
}

function EmptyToday({
  onRun,
  running,
  filter,
}: {
  onRun: () => void;
  running: boolean;
  filter: Filter;
}) {
  const msg =
    filter === "applications"
      ? "No application nudges today."
      : filter === "referrals"
      ? "No referral nudges today."
      : "Nothing on your plate today.";

  return (
    <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-8 text-center">
      <div className="inline-grid place-items-center w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 mb-3">
        <Sparkles className="w-5 h-5" />
      </div>
      <div className="text-[15px] font-semibold text-[var(--color-text)] mb-1">{msg}</div>
      <p className="text-[13px] text-[var(--color-text-3)] max-w-md mx-auto mb-4">
        Either you&apos;re fully caught up or no rules triggered. Try{" "}
        <em>Run check</em> to recompute.
      </p>
      <Button onClick={onRun} disabled={running} className="gap-2">
        <PlayCircle className="w-4 h-4" />
        {running ? "Running…" : "Run check"}
      </Button>
    </div>
  );
}
