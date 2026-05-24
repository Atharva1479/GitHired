"use client";

import { useEffect } from "react";
import { Loader2, Sparkles } from "lucide-react";

import { useAnalyzeDsaProblem } from "@/hooks/useDsa";
import type { DsaAnalysisOut } from "@/lib/types";

interface AnalysisPanelProps {
  problemId: number;
  hasSolution: boolean;
  analysis: DsaAnalysisOut | null;
  autoAnalyze?: boolean;
}

export function AnalysisPanel({
  problemId,
  hasSolution,
  analysis,
  autoAnalyze = false,
}: AnalysisPanelProps) {
  const analyze = useAnalyzeDsaProblem();
  // Use mutation result immediately — don't wait for cache refetch
  const displayAnalysis = analyze.data ?? analysis;

  useEffect(() => {
    if (autoAnalyze && hasSolution && !analysis) {
      analyze.mutate(problemId);
    }
    // only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!hasSolution) {
    return (
      <p className="text-[13px] text-[var(--color-text-3)] italic">
        Add your solution code to enable AI analysis.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-[var(--color-text)]">AI Analysis</h3>
        <button
          type="button"
          onClick={() => analyze.mutate(problemId)}
          disabled={analyze.isPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-60"
        >
          {analyze.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Sparkles className="w-3 h-3" />
          )}
          {analyze.isPending ? "Analyzing…" : displayAnalysis ? "Re-analyze" : "Analyze"}
        </button>
      </div>

      {analyze.isError ? (
        <p className="text-[12px] text-rose-500">Analysis failed. Try again.</p>
      ) : null}

      {analyze.isPending && !displayAnalysis ? (
        <div className="space-y-3 animate-pulse">
          <div className="flex gap-4">
            <div className="flex-1 h-16 rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)]" />
            <div className="flex-1 h-16 rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)]" />
          </div>
          <div className="h-20 rounded-lg bg-[var(--color-surface-2)]" />
          <div className="h-32 rounded-lg bg-[var(--color-surface-2)]" />
        </div>
      ) : null}

      {displayAnalysis ? (
        <div className="space-y-4">
          <div className="flex gap-4">
            <ComplexityCard label="Time Complexity" value={displayAnalysis.time_complexity} />
            <ComplexityCard label="Space Complexity" value={displayAnalysis.space_complexity} />
          </div>

          <Section title="Approach">
            <p className="text-[14px] text-[var(--color-text)] leading-relaxed">
              {displayAnalysis.approach_summary}
            </p>
          </Section>

          <Section title="Feedback">
            <p className="text-[14px] text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
              {displayAnalysis.feedback}
            </p>
          </Section>

          <Section title="Optimized Solution">
            {displayAnalysis.optimized_explanation ? (
              <p className="text-[14px] text-[var(--color-text)] leading-relaxed mb-3">
                {displayAnalysis.optimized_explanation}
              </p>
            ) : null}
            <pre className="text-[12px] font-mono bg-[var(--color-surface-2)] rounded-lg p-4 overflow-x-auto ring-1 ring-[var(--color-border)] text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
              {displayAnalysis.optimized_solution}
            </pre>
          </Section>

          {displayAnalysis.dry_run_explanation ? (
            <Section title="Dry Run — Step-by-Step Trace">
              <div className="bg-indigo-500/5 ring-1 ring-indigo-500/20 rounded-lg p-4">
                <p className="text-[13px] text-[var(--color-text)] leading-relaxed whitespace-pre-wrap font-mono">
                  {displayAnalysis.dry_run_explanation}
                </p>
              </div>
            </Section>
          ) : null}

          <p className="text-[10.5px] text-[var(--color-text-3)]">
            Analyzed by {displayAnalysis.model} · {new Date(displayAnalysis.created_at).toLocaleString()}
          </p>
        </div>
      ) : !analyze.isPending && !displayAnalysis ? (
        <p className="text-[13px] text-[var(--color-text-3)]">
          Click Analyze to get complexity analysis, feedback, optimized solution, and a dry run walkthrough.
        </p>
      ) : null}
    </div>
  );
}

function ComplexityCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex-1 rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] p-3">
      <p className="text-[10.5px] text-[var(--color-text-3)] uppercase tracking-wider mb-1">{label}</p>
      <code className="text-[18px] font-bold font-mono text-violet-600 dark:text-violet-400">
        {value}
      </code>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-3)] mb-2">
        {title}
      </h4>
      {children}
    </div>
  );
}
