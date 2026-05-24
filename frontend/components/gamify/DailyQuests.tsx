"use client";

import {
  ArrowUpRight,
  Briefcase,
  CalendarRange,
  Check,
  Clock,
  type LucideIcon,
  Medal,
  Send,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useGamifyState } from "@/hooks/useGamify";
import type { GamifyQuest } from "@/lib/api";

type Difficulty = "easy" | "medium" | "hard";

function difficultyFor(rewardXp: number): Difficulty {
  if (rewardXp <= 50) return "easy";
  if (rewardXp <= 150) return "medium";
  return "hard";
}

const DIFFICULTY_DOT: Record<Difficulty, string> = {
  easy: "bg-emerald-500",
  medium: "bg-amber-500",
  hard: "bg-rose-500",
};

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

function formatTimeLeft(iso: string): string | null {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return null;
  const hours = Math.floor(ms / 36e5);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const rem = hours % 24;
    return rem > 0 ? `${days}d ${rem}h` : `${days}d`;
  }
  if (hours >= 1) {
    const mins = Math.floor((ms / 6e4) % 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  const mins = Math.max(1, Math.floor(ms / 6e4));
  return `${mins}m`;
}

type Cosmetic = {
  Icon: LucideIcon;
  gradient: string;
  bar: string;
};

function cosmeticFor(code: string): Cosmetic {
  if (code.includes("apply"))
    return {
      Icon: Briefcase,
      gradient: "from-indigo-500 to-violet-500",
      bar: "from-indigo-500 to-violet-500",
    };
  if (code.includes("status"))
    return {
      Icon: ArrowUpRight,
      gradient: "from-amber-500 to-orange-500",
      bar: "from-amber-500 to-orange-500",
    };
  if (code.includes("pipeline") || code.includes("offer"))
    return {
      Icon: TrendingUp,
      gradient: "from-emerald-500 to-teal-500",
      bar: "from-emerald-500 to-teal-500",
    };
  if (code.includes("referral"))
    return {
      Icon: Users,
      gradient: "from-rose-500 to-pink-500",
      bar: "from-rose-500 to-pink-500",
    };
  if (code.includes("followup"))
    return {
      Icon: Send,
      gradient: "from-sky-500 to-cyan-500",
      bar: "from-sky-500 to-cyan-500",
    };
  return {
    Icon: Target,
    gradient: "from-gray-500 to-gray-600",
    bar: "from-gray-500 to-gray-600",
  };
}

export function DailyQuests() {
  const { data, isLoading } = useGamifyState();
  const previousProgress = useRef<Record<string, number>>({});
  const [popped, setPopped] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!data) return;
    const next = new Set<string>();
    for (const q of [...data.daily_quests, ...data.weekly_quests]) {
      const prev = previousProgress.current[q.code] ?? 0;
      if (q.completed && prev < q.target) next.add(q.code);
      previousProgress.current[q.code] = q.progress;
    }
    if (next.size > 0) {
      setPopped(next);
      const t = window.setTimeout(() => setPopped(new Set()), 700);
      return () => window.clearTimeout(t);
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-4 shadow-sm">
        <div className="h-4 w-32 bg-[var(--color-surface-2)] rounded animate-pulse mb-3" />
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-11 bg-[var(--color-surface-2)] rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const daily = data?.daily_quests ?? [];
  const weekly = data?.weekly_quests ?? [];
  if (daily.length === 0 && weekly.length === 0) return null;

  const dailyDone = daily.filter((q) => q.completed).length;
  const dailyTotal = daily.length;
  const allDone = dailyTotal > 0 && dailyDone === dailyTotal;

  return (
    <div
      className={`relative rounded-2xl bg-[var(--color-surface)] ring-1 p-4 shadow-sm overflow-hidden transition-all ${
        allDone
          ? "ring-emerald-500/30 bg-gradient-to-br from-emerald-500/10 via-[var(--color-surface)] to-[var(--color-surface)]"
          : "ring-[var(--color-border)]"
      }`}
    >
      {allDone ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(circle at top right, rgba(16,185,129,0.22), transparent 55%)",
          }}
        />
      ) : null}

      <header className="relative flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {allDone ? (
            <Medal className="w-[18px] h-[18px] text-emerald-400" />
          ) : (
            <Target className="w-4 h-4 text-indigo-400" />
          )}
          <h2 className="text-[13.5px] font-semibold text-[var(--color-text)]">
            {allDone ? "Daily goal smashed!" : "Today's quests"}
          </h2>
          {daily[0]?.expires_at && !allDone ? (
            <span className="hidden sm:inline-flex items-center gap-1 text-[10.5px] text-[var(--color-text-3)] font-medium">
              <Clock className="w-3 h-3" />
              Resets in {formatTimeLeft(daily[0].expires_at) ?? "0m"}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            {Array.from({ length: dailyTotal }).map((_, i) => (
              <span
                key={i}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${
                  i < dailyDone
                    ? allDone
                      ? "bg-emerald-500"
                      : "bg-indigo-500"
                    : "bg-[var(--color-border)]"
                }`}
              />
            ))}
          </div>
          <span className="text-[11.5px] tabular-nums font-semibold text-[var(--color-text-2)]">
            {dailyDone}/{dailyTotal}
          </span>
        </div>
      </header>

      <ul className="relative space-y-1.5">
        {daily.map((q) => (
          <QuestRow
            key={q.code}
            quest={q}
            popped={popped.has(q.code)}
          />
        ))}
      </ul>

      {weekly.length > 0 ? (
        <div className="relative mt-3 pt-3 border-t border-[var(--color-border)] space-y-1.5">
          <div className="flex items-center gap-1.5 text-[9.5px] uppercase tracking-widest font-bold text-[var(--color-text-3)] mb-1.5">
            <CalendarRange className="w-3 h-3" />
            This week
          </div>
          {weekly.map((q) => (
            <QuestRow
              key={q.code}
              quest={q}
              popped={popped.has(q.code)}
              compact
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function QuestRow({
  quest,
  popped,
  compact = false,
}: {
  quest: GamifyQuest;
  popped: boolean;
  compact?: boolean;
}) {
  const { Icon, gradient, bar } = cosmeticFor(quest.code);
  const pct = Math.min(1, quest.progress / Math.max(1, quest.target));
  const pctInt = Math.round(pct * 100);
  const done = quest.completed;
  const difficulty = difficultyFor(quest.reward_xp);

  return (
    <li
      className={`group flex items-center gap-3 rounded-xl px-2 py-1.5 transition-all ${
        done ? "bg-emerald-500/10" : "hover:bg-[var(--color-surface-2)]"
      } ${popped ? "ring-pop" : ""}`}
      title={quest.title}
    >
      {/* Icon avatar */}
      <span
        className={`relative grid place-items-center rounded-lg shrink-0 text-white shadow-sm ${
          done ? "bg-emerald-500" : `bg-gradient-to-br ${gradient}`
        }`}
        style={{ width: compact ? 28 : 32, height: compact ? 28 : 32 }}
      >
        {done ? (
          <Check className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
        ) : (
          <Icon className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
        )}
      </span>

      {/* Title + progress */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {!done ? (
            <span
              aria-label={`Difficulty: ${DIFFICULTY_LABEL[difficulty]}`}
              title={`Difficulty: ${DIFFICULTY_LABEL[difficulty]}`}
              className={`shrink-0 w-1.5 h-1.5 rounded-full ${DIFFICULTY_DOT[difficulty]}`}
            />
          ) : null}
          <span
            className={`text-[12.5px] font-semibold truncate ${
              done ? "line-through text-[var(--color-text-3)]" : "text-[var(--color-text)]"
            }`}
          >
            {quest.title}
          </span>
          <span className="ml-auto shrink-0 flex items-center gap-1.5">
            <span className="text-[10.5px] tabular-nums text-[var(--color-text-3)] font-medium">
              {quest.progress}/{quest.target}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-1.5 text-[9.5px] font-bold tracking-tight tabular-nums ${
                done
                  ? "bg-emerald-500/15 text-emerald-400"
                  : compact
                    ? "bg-amber-500/15 text-amber-400"
                    : "bg-indigo-500/15 text-indigo-400"
              }`}
            >
              +{quest.reward_xp}
            </span>
          </span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <div className="flex-1 h-1 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-700 ease-out ${
                done ? "from-emerald-400 to-emerald-500" : bar
              }`}
              style={{ width: `${pct * 100}%` }}
            />
          </div>
          <span className="text-[10px] tabular-nums text-[var(--color-text-3)] w-7 text-right">
            {pctInt}%
          </span>
        </div>
      </div>
    </li>
  );
}
