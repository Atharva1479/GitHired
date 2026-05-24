"use client";

/**
 * Slim animated bar — done count / total. Color shifts from indigo to
 * emerald as the percentage climbs so progress *feels* like progress.
 * Pure CSS, no JS animation work.
 */
export function StudyProgressBar({
  done,
  total,
  showLabel = true,
}: {
  done: number;
  total: number;
  showLabel?: boolean;
}) {
  if (total === 0) return null;
  const pct = Math.round((done / total) * 100);
  const fill =
    pct >= 100
      ? "bg-emerald-500"
      : pct >= 60
        ? "bg-gradient-to-r from-indigo-500 to-emerald-500"
        : pct >= 25
          ? "bg-indigo-500"
          : "bg-indigo-400";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${fill}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel ? (
        <span className="shrink-0 text-[11px] tabular-nums text-[var(--color-text-3)] font-medium">
          {done}/{total}
        </span>
      ) : null}
    </div>
  );
}
