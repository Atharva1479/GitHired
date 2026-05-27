"use client";

import { type Application, type Status, STATUS_META } from "@/lib/types";
import { Card } from "./Card";

interface ColumnProps {
  status: Status;
  apps: Application[];
  draggingId: number | null;
  isOver: boolean;
  onOpenCard: (id: number) => void;
  onDragStart: (id: number) => void;
  onDragEnd: () => void;
  onDragOver: () => void;
  onDragLeave: () => void;
  onDrop: () => void;
}

export function Column({
  status,
  apps,
  draggingId,
  isOver,
  onOpenCard,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop,
}: ColumnProps) {
  const meta = STATUS_META[status];

  return (
    <div
      className="flex flex-col shrink-0 w-[248px] rounded-2xl transition-colors duration-150"
      style={{
        background: isOver
          ? "rgba(99,102,241,0.06)"
          : "var(--color-surface-2)",
        border: isOver
          ? "1.5px solid rgba(99,102,241,0.35)"
          : "1.5px solid var(--color-border)",
      }}
      onDragOver={(e) => { e.preventDefault(); onDragOver(); }}
      onDragLeave={onDragLeave}
      onDrop={(e) => { e.preventDefault(); onDrop(); }}
    >
      {/* Column header */}
      <div className="px-3.5 pt-3.5 pb-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${meta.dot}`} />
            <span className="text-[13px] font-semibold text-[var(--color-text)]">
              {meta.label}
            </span>
          </div>
          <span className="min-w-[20px] text-center text-[11px] font-semibold text-[var(--color-text-3)] bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] rounded-full px-1.5 py-0.5 tabular-nums">
            {apps.length}
          </span>
        </div>
        {/* accent bar */}
        <div className={`mt-2.5 h-0.5 rounded-full ${meta.columnAccent} opacity-70`} />
      </div>

      {/* Cards */}
      <div className="flex flex-col gap-2 px-2.5 pb-2.5 overflow-y-auto max-h-[calc(100vh-280px)] min-h-[80px]">
        {apps.length === 0 ? (
          <div className="flex items-center justify-center h-16 rounded-xl border border-dashed border-[var(--color-border)] text-[11.5px] text-[var(--color-text-3)]">
            {isOver ? "Drop here" : "No applications"}
          </div>
        ) : (
          apps.map((app) => (
            <Card
              key={app.id}
              app={app}
              dragging={draggingId === app.id}
              onOpen={() => onOpenCard(app.id)}
              onDragStart={() => onDragStart(app.id)}
              onDragEnd={onDragEnd}
            />
          ))
        )}

        {/* Drop indicator when dragging over a non-empty column */}
        {isOver && apps.length > 0 && (
          <div className="h-1 rounded-full bg-indigo-400 opacity-60 mx-1" />
        )}
      </div>
    </div>
  );
}
