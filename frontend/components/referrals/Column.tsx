"use client";

import { useDroppable } from "@dnd-kit/core";

import { CONN_STATUS_META, type ConnectionStatus, type Referral } from "@/lib/referrals";

import { ReferralCard } from "./Card";

export function ReferralColumn({
  status,
  refs,
  onOpenCard,
}: {
  status: ConnectionStatus;
  refs: Referral[];
  onOpenCard?: (id: number) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const meta = CONN_STATUS_META[status];

  return (
    <div
      ref={setNodeRef}
      className={`flex-shrink-0 w-[300px] flex flex-col rounded-2xl bg-[var(--color-surface)] ring-1 transition-colors ${
        isOver ? "ring-indigo-400 bg-indigo-500/10" : "ring-[var(--color-border)]"
      }`}
    >
      <div className={`h-1 rounded-t-2xl ${meta.columnAccent}`} aria-hidden />

      <header className="flex items-center justify-between gap-2 px-4 pt-3 pb-2">
        <div className="flex items-center gap-2">
          <span aria-hidden className={`w-2 h-2 rounded-full ${meta.dot}`} />
          <span className="text-[13px] font-semibold text-[var(--color-text)]">
            {meta.label}
          </span>
        </div>
        <span className="text-[11px] font-medium text-[var(--color-text-3)] bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] rounded-full px-2 py-0.5 tabular-nums">
          {refs.length}
        </span>
      </header>

      <div className="px-3 pb-3 space-y-2 flex-1 min-h-[120px]">
        {refs.map((r) => (
          <ReferralCard key={r.id} ref={r} draggable onOpen={onOpenCard} />
        ))}
        {refs.length === 0 ? (
          <div className="grid place-items-center h-24 border-2 border-dashed border-[var(--color-border)] rounded-xl text-[12px] text-[var(--color-text-3)]">
            No contacts
          </div>
        ) : null}
      </div>
    </div>
  );
}
