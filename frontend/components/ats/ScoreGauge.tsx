"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  score: number;
  grade: string;
}

function scoreColor(score: number) {
  if (score >= 70) return { stroke: "#10b981", text: "text-emerald-500", bg: "bg-emerald-500/10 text-emerald-600" };
  if (score >= 50) return { stroke: "#f59e0b", text: "text-amber-500", bg: "bg-amber-500/10 text-amber-600" };
  return { stroke: "#ef4444", text: "text-red-500", bg: "bg-red-500/10 text-red-500" };
}

export function ScoreGauge({ score, grade }: Props) {
  const [displayed, setDisplayed] = useState(0);
  const rafRef = useRef<number | null>(null);
  const colors = scoreColor(score);

  const radius = 80;
  const cx = 100;
  const cy = 100;
  const circumference = 2 * Math.PI * radius;
  const progress = (displayed / 100) * circumference;
  const dashOffset = circumference - progress;

  useEffect(() => {
    const start = performance.now();
    const duration = 1500;

    function tick(now: number) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayed(Math.round(eased * score));
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [score]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-[200px] h-[200px]">
        <svg viewBox="0 0 200 200" className="w-full h-full -rotate-90">
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke="var(--color-border)"
            strokeWidth={14}
          />
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={14}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{ transition: "none" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-[42px] font-bold tabular-nums leading-none ${colors.text}`}>
            {displayed}
          </span>
          <span className="text-[13px] text-[var(--color-text-3)] mt-0.5">/ 100</span>
        </div>
      </div>
      <span
        className={`text-[13px] font-semibold px-3 py-1 rounded-full ring-1 ring-inset ${
          score >= 70
            ? "bg-emerald-500/10 text-emerald-600 ring-emerald-300/40"
            : score >= 50
            ? "bg-amber-500/10 text-amber-600 ring-amber-300/40"
            : "bg-red-500/10 text-red-500 ring-red-300/40"
        }`}
      >
        Grade {grade}
      </span>
    </div>
  );
}
