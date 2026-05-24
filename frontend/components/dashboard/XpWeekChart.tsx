"use client";

import { useGamifyState } from "@/hooks/useGamify";

const DAYS = ["M", "T", "W", "T", "F", "S", "S"];

export function XpWeekChart() {
  const { data } = useGamifyState();
  if (!data) return null;

  const streakDays = Math.min(data.streak, 7);
  const today = new Date().getDay();
  // Convert JS day (0=Sun) to Mon-first index
  const todayIdx = today === 0 ? 6 : today - 1;

  const bars = DAYS.map((_, i) => {
    const daysAgo = todayIdx - i;
    if (daysAgo < 0) return 0;
    if (daysAgo >= streakDays) return 0;
    if (daysAgo === 0) {
      return Math.max(10, Math.round((data.xp_into_level / Math.max(1, data.xp_for_level)) * 100));
    }
    // Prior days: estimate from streak — earlier = slightly less
    return Math.max(10, 60 - daysAgo * 5);
  });

  const maxBar = Math.max(...bars, 1);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          XP This Week
        </span>
        <span className="text-[10px] text-[var(--color-text-3)]">{data.xp_into_level} XP</span>
      </div>
      <div className="flex items-end gap-1 h-9">
        {bars.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm transition-[height] duration-500"
            style={{
              height: `${Math.max(4, (h / maxBar) * 100)}%`,
              background: h > 0
                ? (i === todayIdx ? "#8b6de0" : "#8b6de070")
                : "var(--color-surface-2)",
            }}
          />
        ))}
      </div>
      <div className="flex gap-1 mt-1.5">
        {DAYS.map((d, i) => (
          <div
            key={i}
            className="flex-1 text-center text-[8.5px] font-bold uppercase"
            style={{
              color: bars[i] > 0 ? "var(--color-text-3)" : "var(--color-border)",
            }}
          >
            {d}
          </div>
        ))}
      </div>
    </div>
  );
}
