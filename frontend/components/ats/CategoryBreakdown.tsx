"use client";

import { useEffect, useState } from "react";
import type { AnalysisResult } from "@/types/ats";

interface Props {
  categories: AnalysisResult["categories"];
}

const ML_KEYS = new Set(["semantic_sentence", "word_semantic"]);

function barColor(score: number) {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function scoreTextColor(score: number) {
  if (score >= 70) return "text-emerald-500";
  if (score >= 50) return "text-amber-500";
  return "text-red-500";
}

export function CategoryBreakdown({ categories }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 80);
    return () => clearTimeout(t);
  }, []);

  const rows = Object.entries(categories) as [
    keyof typeof categories,
    (typeof categories)[keyof typeof categories],
  ][];

  return (
    <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
      <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-4">
        Category Breakdown
      </h2>
      <div className="space-y-4">
        {rows.map(([key, cat], i) => (
          <div
            key={key}
            style={{
              opacity: mounted ? 1 : 0,
              transform: mounted ? "translateY(0)" : "translateY(6px)",
              transition: `opacity 0.3s ease ${i * 80}ms, transform 0.3s ease ${i * 80}ms`,
            }}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-[var(--color-text)]">
                  {cat.label}
                </span>
                {ML_KEYS.has(key) && (
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-600 ring-1 ring-violet-300/40">
                    ML
                  </span>
                )}
                <span className="text-[11px] text-[var(--color-text-3)] bg-[var(--color-surface-2)] px-1.5 py-0.5 rounded-md">
                  {cat.weight}%
                </span>
              </div>
              <span className={`text-[13px] font-semibold tabular-nums ${scoreTextColor(cat.score)}`}>
                {cat.score}
                <span className="text-[11px] text-[var(--color-text-3)] font-normal">/100</span>
              </span>
            </div>
            <div className="h-2 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
              <div
                className={`h-full rounded-full ${barColor(cat.score)}`}
                style={{
                  width: mounted ? `${cat.score}%` : "0%",
                  transition: `width 0.7s ease ${i * 80 + 200}ms`,
                }}
              />
            </div>
            <p className="text-[12px] text-[var(--color-text-3)] mt-1">{cat.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
