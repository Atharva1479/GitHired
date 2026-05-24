"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { AddProblemModal } from "@/components/dsa/AddProblemModal";
import { DsaStatsStrip } from "@/components/dsa/StatsStrip";
import { TopicSidebar } from "@/components/dsa/TopicSidebar";
import { ProblemCard } from "@/components/dsa/ProblemCard";
import { ProblemDetail } from "@/components/dsa/ProblemDetail";
import { useDsaProblems, useDsaStats } from "@/hooks/useDsa";
import type { DsaProblemOut } from "@/lib/types";

export default function DsaPage() {
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [addOpen, setAddOpen] = useState(false);
  const [selected, setSelected] = useState<DsaProblemOut | null>(null);
  const [autoAnalyze, setAutoAnalyze] = useState(false);

  const { data: stats } = useDsaStats();
  const { data: problems, isLoading } = useDsaProblems(topic);

  function handleCreated(problem: DsaProblemOut) {
    setSelected(problem);
    setAutoAnalyze(true);
  }

  function handleCloseDetail() {
    setSelected(null);
    setAutoAnalyze(false);
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-[22px] font-bold text-[var(--color-text)]">DSA Practice</h1>
            <p className="text-[13px] text-[var(--color-text-3)] mt-0.5">
              Track solved problems, get AI complexity analysis
            </p>
          </div>
          <button
            type="button"
            onClick={() => setAddOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[14px] font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Log Problem
          </button>
        </div>

        {stats ? <DsaStatsStrip stats={stats} /> : null}

        <div className="flex gap-6">
          <TopicSidebar
            topics={stats?.topics ?? []}
            selected={topic}
            onSelect={setTopic}
          />

          <div className="flex-1 min-w-0">
            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-24 rounded-xl ring-1 ring-[var(--color-border)] bg-[var(--color-surface)] animate-pulse"
                  />
                ))}
              </div>
            ) : !problems?.length ? (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <p className="text-4xl mb-3">🧩</p>
                <p className="text-[16px] font-medium text-[var(--color-text)]">No problems yet</p>
                <p className="text-[13px] text-[var(--color-text-3)] mt-1">
                  {topic
                    ? `No ${topic} problems logged.`
                    : "Log your first solved problem to get started."}
                </p>
                <button
                  type="button"
                  onClick={() => setAddOpen(true)}
                  className="mt-4 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[14px] font-medium transition-colors"
                >
                  Log a Problem
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {problems.map((p) => (
                  <ProblemCard
                    key={p.id}
                    problem={p}
                    onClick={() => {
                      setSelected(p);
                      setAutoAnalyze(false);
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <AddProblemModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={handleCreated}
      />

      {selected ? (
        <ProblemDetail
          problem={selected}
          onClose={handleCloseDetail}
          autoAnalyze={autoAnalyze}
        />
      ) : null}
    </AppShell>
  );
}
