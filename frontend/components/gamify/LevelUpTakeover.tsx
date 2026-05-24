"use client";

import confetti from "canvas-confetti";
import { ChevronRight, Crown, Sparkles } from "lucide-react";
import { useEffect } from "react";

import { rankForLevel } from "@/lib/rank";
import { haptic, sfx } from "@/lib/sfx";

const RANK_GRADIENT: Record<string, string> = {
  bronze:
    "bg-gradient-to-br from-amber-500 via-orange-500 to-red-500",
  silver:
    "bg-gradient-to-br from-slate-300 via-slate-400 to-slate-600",
  gold: "bg-gradient-to-br from-yellow-400 via-amber-500 to-orange-500",
  platinum:
    "bg-gradient-to-br from-indigo-400 via-violet-500 to-fuchsia-500",
  diamond:
    "bg-gradient-to-br from-cyan-400 via-sky-500 to-indigo-500",
  master:
    "bg-gradient-to-br from-fuchsia-500 via-pink-500 to-rose-500",
};

export function LevelUpTakeover({
  level,
  previousLevel,
  onClose,
}: {
  level: number;
  previousLevel: number;
  onClose: () => void;
}) {
  const rank = rankForLevel(level);
  const previousRank = rankForLevel(Math.max(1, previousLevel));
  const rankAdvanced = rank.tier !== previousRank.tier;
  const gradient = RANK_GRADIENT[rank.tier] ?? RANK_GRADIENT.bronze;

  // Sound + haptic on mount.
  useEffect(() => {
    sfx.unlock();
    sfx.levelUp();
    haptic(rankAdvanced ? [20, 40, 20, 40, 60] : [20, 30, 20]);
    fireConfetti(rankAdvanced);
    // Auto-dismiss after 5s.
    const t = window.setTimeout(onClose, 5000);
    return () => window.clearTimeout(t);
  }, [onClose, rankAdvanced]);

  // ESC to close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Enter") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Level ${level} reached`}
      onClick={onClose}
      className="fixed inset-0 z-[70] flex items-center justify-center bg-gray-950/70 backdrop-blur-sm overflow-hidden"
    >
      {/* Expanding radial pulse rings */}
      <span
        aria-hidden
        className="absolute w-[300px] h-[300px] rounded-full bg-white/10 radial-pulse"
        style={{ animationDelay: "0ms" }}
      />
      <span
        aria-hidden
        className="absolute w-[300px] h-[300px] rounded-full bg-white/10 radial-pulse"
        style={{ animationDelay: "300ms" }}
      />
      <span
        aria-hidden
        className="absolute w-[300px] h-[300px] rounded-full bg-white/10 radial-pulse"
        style={{ animationDelay: "600ms" }}
      />

      {/* Floating sparkles */}
      <Sparkles
        aria-hidden
        className="absolute top-[22%] left-[28%] w-6 h-6 text-yellow-300 sparkle-twinkle"
        style={{ animationDelay: "200ms" }}
      />
      <Sparkles
        aria-hidden
        className="absolute bottom-[28%] right-[26%] w-5 h-5 text-fuchsia-300 sparkle-twinkle"
        style={{ animationDelay: "500ms" }}
      />
      <Sparkles
        aria-hidden
        className="absolute top-[34%] right-[22%] w-4 h-4 text-cyan-300 sparkle-twinkle"
        style={{ animationDelay: "800ms" }}
      />

      <div
        onClick={(e) => e.stopPropagation()}
        className="relative flex flex-col items-center text-center px-6 max-w-sm"
      >
        <p className="title-pop text-[11px] font-bold uppercase tracking-[0.25em] text-white/80 mb-3">
          {rankAdvanced ? "Rank up" : "Level up"}
        </p>

        {/* The badge */}
        <div className="relative mb-5">
          <div
            className={`badge-spin-in relative grid place-items-center w-32 h-32 rounded-full ${gradient} text-white shadow-[0_20px_60px_rgba(0,0,0,0.45)] ring-4 ring-white/20`}
          >
            <span className="text-[58px] font-black tabular-nums leading-none drop-shadow-lg">
              {level}
            </span>
            {level >= 5 ? (
              <Crown className="absolute -top-3 w-8 h-8 text-yellow-300 drop-shadow-lg" />
            ) : null}
          </div>
          <div
            aria-hidden
            className="absolute inset-0 rounded-full aura-breathe"
            style={{
              background:
                "radial-gradient(circle, rgba(255,255,255,0.35), transparent 65%)",
            }}
          />
        </div>

        <h2 className="title-pop text-[28px] font-black tracking-tight text-white leading-tight">
          {rankAdvanced ? rank.title : `Level ${level}`}
        </h2>
        {rankAdvanced ? (
          <p className="title-pop mt-1 text-[13px] text-white/70">
            You ranked up from {previousRank.title}
          </p>
        ) : (
          <p className="title-pop mt-1 text-[13px] text-white/70">
            Still climbing as {rank.title}
          </p>
        )}

        <button
          type="button"
          onClick={onClose}
          className="fade-up mt-7 inline-flex items-center gap-1.5 rounded-full bg-white text-gray-900 font-semibold px-5 h-10 text-[13px] shadow-xl hover:bg-gray-100 transition-colors"
          style={{ animationDelay: "500ms" }}
        >
          Continue
          <ChevronRight className="w-4 h-4" />
        </button>
        <p
          className="fade-up text-[10.5px] uppercase tracking-widest text-white/50 mt-3"
          style={{ animationDelay: "700ms" }}
        >
          Tap anywhere to dismiss
        </p>
      </div>
    </div>
  );
}

function fireConfetti(big: boolean) {
  const duration = big ? 2400 : 1500;
  const end = Date.now() + duration;
  const palette = big
    ? ["#fbbf24", "#f472b6", "#a78bfa", "#60a5fa", "#34d399"]
    : ["#6366f1", "#8b5cf6", "#d946ef", "#f59e0b"];

  const tick = () => {
    confetti({
      particleCount: big ? 6 : 4,
      angle: 60,
      spread: 60,
      origin: { x: 0, y: 0.7 },
      colors: palette,
      scalar: big ? 1.15 : 1,
    });
    confetti({
      particleCount: big ? 6 : 4,
      angle: 120,
      spread: 60,
      origin: { x: 1, y: 0.7 },
      colors: palette,
      scalar: big ? 1.15 : 1,
    });
    if (Date.now() < end) requestAnimationFrame(tick);
  };
  tick();

  if (big) {
    // Initial burst from center for rank-ups.
    confetti({
      particleCount: 120,
      spread: 100,
      origin: { x: 0.5, y: 0.55 },
      colors: palette,
      scalar: 1.3,
      startVelocity: 45,
    });
  }
}

