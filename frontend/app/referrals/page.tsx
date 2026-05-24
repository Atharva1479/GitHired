"use client";

import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { AddReferral } from "@/components/referrals/AddReferral";
import { ReferralBoard } from "@/components/referrals/Board";
import { ReferralDetail } from "@/components/referrals/ReferralDetail";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { useReferrals } from "@/hooks/useReferrals";

export default function ReferralsPage() {
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data } = useReferrals();

  const stats = useMemo(() => {
    const refs = data ?? [];
    const pending = refs.filter((r) =>
      ["Request Sent", "Accepted", "Msg Sent"].includes(r.connection_status),
    ).length;
    const referred = refs.filter((r) => r.connection_status === "Referred").length;
    const closed = refs.filter((r) =>
      ["Referred", "Dropped"].includes(r.connection_status),
    );
    const conversionRate =
      closed.length === 0
        ? 0
        : Math.round(
            (closed.filter((r) => r.connection_status === "Referred").length /
              closed.length) *
              100,
          );
    return { total: refs.length, pending, referred, conversionRate };
  }, [data]);

  return (
    <AppShell>
      <main className="flex-1 flex flex-col">
        <div className="max-w-[1400px] w-full mx-auto px-6 pt-8 pb-4">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-[26px] font-bold tracking-tight text-[var(--color-text)]">
                Referrals
              </h1>
              <p className="text-[14px] text-[var(--color-text-3)] mt-1">
                Track LinkedIn connections, who you&apos;ve asked, and who came through.
              </p>
            </div>
            <Button onClick={() => setOpen(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Add referral
            </Button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
            <Stat label="Total" value={stats.total} tone="indigo" />
            <Stat label="In progress" value={stats.pending} tone="amber" />
            <Stat label="Referred" value={stats.referred} tone="emerald" />
            <Stat
              label="Conversion"
              value={`${stats.conversionRate}%`}
              tone="violet"
            />
          </div>
        </div>

        <ReferralBoard onOpenCard={setSelectedId} />

        <AddReferral open={open} onClose={() => setOpen(false)} />
        <ReferralDetail
          refId={selectedId}
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
