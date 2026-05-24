"use client";

import { useEffect, useRef, useState } from "react";
import { useGamifyState } from "@/hooks/useGamify";
import type { GamifyQuest } from "@/lib/api";

type Difficulty = "Easy" | "Medium" | "Hard";

function diffOf(xp: number): Difficulty {
  if (xp <= 50) return "Easy";
  if (xp <= 150) return "Medium";
  return "Hard";
}

function formatReset(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "expired";
  const h = Math.floor(ms / 36e5);
  const m = Math.floor((ms % 36e5) / 6e4);
  if (h >= 1) return m > 0 ? `${h}h ${m}m` : `${h}h`;
  return `${Math.max(1, m)}m`;
}

const DIFF_STYLE: Record<Difficulty, string> = {
  Easy:   "bg-emerald-500/10 text-emerald-600 dark:text-[#3daa7a]",
  Medium: "bg-amber-500/10   text-amber-600   dark:text-[#c89040]",
  Hard:   "bg-rose-500/10    text-rose-600    dark:text-[#c06060]",
};

function dotColor(code: string): string {
  if (code.includes("apply") || code.includes("pipeline")) return "#5a90d8";
  if (code.includes("study") || code.includes("review"))   return "#8b6de0";
  if (code.includes("referral") || code.includes("followup")) return "#3daa7a";
  return "#70707a";
}

function QuestRow({ quest }: { quest: GamifyQuest }) {
  const done = quest.completed;
  const pct = Math.min(1, quest.progress / Math.max(1, quest.target));
  const diff = diffOf(quest.reward_xp);
  const color = dotColor(quest.code);
  const showProg = quest.target > 1;

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2.5 border-b border-[var(--color-border-2)] last:border-b-0 ${
        done ? "opacity-40" : ""
      }`}
    >
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ background: done ? "var(--color-text-3)" : color }}
      />
      <span
        className={`flex-1 text-[12.5px] min-w-0 truncate ${
          done
            ? "line-through text-[var(--color-text-3)]"
            : "text-[var(--color-text-2)]"
        }`}
      >
        {quest.title}
      </span>
      {showProg && !done && (
        <span className="text-[10.5px] text-[var(--color-text-3)] tabular-nums shrink-0">
          {quest.progress}/{quest.target}
        </span>
      )}
      <span className={`text-[9.5px] font-bold px-2 py-0.5 rounded-full shrink-0 ${DIFF_STYLE[diff]}`}>
        {diff}
      </span>
      <div className="w-10 h-[3px] bg-[var(--color-surface-2)] rounded-full shrink-0 overflow-hidden">
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${pct * 100}%`, background: done ? "var(--color-text-3)" : color }}
        />
      </div>
      <span
        className="text-[10.5px] font-bold min-w-[52px] text-right shrink-0"
        style={{ color: done ? "var(--color-text-3)" : "#9080e0" }}
      >
        {done ? `✓ +${quest.reward_xp}` : `+${quest.reward_xp} XP`}
      </span>
    </div>
  );
}

export function DailyBoard() {
  const { data, isLoading } = useGamifyState();
  const prevProg = useRef<Record<string, number>>({});
  const [, setPopped] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!data) return;
    const next = new Set<string>();
    for (const q of [...data.daily_quests, ...data.weekly_quests]) {
      const prev = prevProg.current[q.code] ?? 0;
      if (q.completed && prev < q.target) next.add(q.code);
      prevProg.current[q.code] = q.progress;
    }
    if (next.size > 0) {
      setPopped(next);
      const t = window.setTimeout(() => setPopped(new Set()), 700);
      return () => window.clearTimeout(t);
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 animate-pulse">
        <div className="h-3 w-24 bg-[var(--color-surface-2)] rounded mb-3" />
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-10 bg-[var(--color-surface-2)] rounded mb-2" />
        ))}
      </div>
    );
  }

  const daily = data?.daily_quests ?? [];
  const weekly = data?.weekly_quests ?? [];
  if (daily.length === 0 && weekly.length === 0) return null;

  const done = daily.filter((q) => q.completed).length;
  const xpEarned = daily.filter((q) => q.completed).reduce((s, q) => s + q.reward_xp, 0);
  const xpLeft = daily.filter((q) => !q.completed).reduce((s, q) => s + q.reward_xp, 0);
  const resetStr = daily[0]?.expires_at ? formatReset(daily[0].expires_at) : null;

  const sorted = [...daily].sort((a, b) =>
    Number(a.completed) - Number(b.completed),
  );

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <span className="text-[10.5px] font-bold uppercase tracking-[0.09em] text-[var(--color-text-3)]">
          Daily Board
        </span>
        <span className="text-[11.5px] text-[#9080e0] font-semibold">
          {xpLeft > 0 ? `${xpLeft} XP left today` : "Daily complete 🎉"}
        </span>
      </div>

      <div>
        {sorted.map((q) => (
          <QuestRow key={q.code} quest={q} />
        ))}
      </div>

      {weekly.length > 0 && (
        <>
          <div className="px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
            <span className="text-[9.5px] font-bold uppercase tracking-widest text-[var(--color-text-3)]">
              This week
            </span>
          </div>
          {weekly.map((q) => (
            <QuestRow key={q.code} quest={q} />
          ))}
        </>
      )}

      <div className="flex items-center justify-between px-4 py-2.5 border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
        <span className="text-[10.5px] text-[var(--color-text-3)]">
          {done}/{daily.length} complete
          {resetStr ? ` · Resets in ${resetStr}` : ""}
        </span>
        <span className="text-[10.5px] font-semibold text-[#9080e0]">
          +{xpEarned} XP earned today
        </span>
      </div>
    </div>
  );
}
