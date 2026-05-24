"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { AddApplication } from "@/components/applications/AddApplication";
import { ApplicationDetail } from "@/components/applications/ApplicationDetail";
import { Board } from "@/components/kanban/Board";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { useApplications } from "@/hooks/useApplications";

export default function ApplicationsPage() {
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data } = useApplications();

  const stats = useMemo(() => {
    const apps = data ?? [];
    const inProgress = apps.filter((a) =>
      ["Applied", "Screening", "Interview"].includes(a.status),
    ).length;
    const offers = apps.filter((a) => a.status === "Offer").length;
    const closed = apps.filter((a) =>
      ["Offer", "Rejected", "Ghosted"].includes(a.status),
    );
    const responseRate =
      closed.length === 0
        ? 0
        : Math.round(
            (closed.filter((a) => a.status !== "Ghosted").length /
              closed.length) *
              100,
          );
    return { total: apps.length, inProgress, offers, responseRate };
  }, [data]);

  return (
    <AppShell>
      <main className="flex-1 flex flex-col">
        <div className="max-w-[1400px] w-full mx-auto px-6 pt-8 pb-4">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-[26px] font-bold tracking-tight text-[var(--color-text)]">
                Applications
              </h1>
              <p className="text-[14px] text-[var(--color-text-3)] mt-1">
                Track every job you&apos;ve applied to. Drag a card to move
                statuses.
              </p>
            </div>
            <Button onClick={() => setOpen(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Add application
            </Button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
            <Stat label="Total" value={stats.total} tone="indigo" />
            <Stat label="In progress" value={stats.inProgress} tone="amber" />
            <Stat label="Offers" value={stats.offers} tone="emerald" />
            <Stat
              label="Response rate"
              value={`${stats.responseRate}%`}
              tone="violet"
            />
          </div>
        </div>

        <Board onOpenCard={setSelectedId} />

        <AddApplication open={open} onClose={() => setOpen(false)} />
        <ApplicationDetail
          appId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      </main>
    </AppShell>
  );
}

const toneClass: Record<string, string> = {
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  amber: "bg-amber-50 text-amber-800 ring-amber-200",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
};

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone: keyof typeof toneClass;
}) {
  return (
    <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-4 shadow-sm">
      <div className="text-[12px] font-medium text-[var(--color-text-3)]">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-[24px] font-semibold text-[var(--color-text)] tabular-nums">
          {value}
        </span>
        <span
          className={`text-[10px] uppercase tracking-wide ring-1 rounded-full px-1.5 py-0.5 ${toneClass[tone]}`}
        >
          live
        </span>
      </div>
    </div>
  );
}
