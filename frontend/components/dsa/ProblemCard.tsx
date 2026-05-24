import { ExternalLink, Sparkles } from "lucide-react";

import type { DsaProblemOut } from "@/lib/types";

const DIFF_STYLES: Record<string, string> = {
  easy: "text-emerald-700 dark:text-emerald-400",
  medium: "text-amber-700 dark:text-amber-400",
  hard: "text-rose-700 dark:text-rose-400",
};

interface ProblemCardProps {
  problem: DsaProblemOut;
  onClick: () => void;
}

export function ProblemCard({ problem, onClick }: ProblemCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-4 hover:ring-indigo-400 hover:shadow-md transition-all group shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-[11px] font-semibold uppercase ${DIFF_STYLES[problem.difficulty]}`}
            >
              {problem.difficulty}
            </span>
            <span className="text-[11px] text-[var(--color-text-3)]">·</span>
            <span className="text-[11px] text-[var(--color-text-3)] truncate">{problem.topic}</span>
          </div>

          <h3 className="text-[14px] font-medium text-[var(--color-text)] truncate group-hover:text-indigo-400 transition-colors">
            {problem.title}
          </h3>

          {problem.description ? (
            <p className="text-[12px] text-[var(--color-text-3)] mt-1 line-clamp-2">
              {problem.description}
            </p>
          ) : null}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {problem.analysis ? (
            <span title="AI analyzed" className="text-violet-500">
              <Sparkles className="w-4 h-4" />
            </span>
          ) : null}
          {problem.source_url ? (
            <a
              href={problem.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          ) : null}
        </div>
      </div>

      {problem.analysis ? (
        <div className="flex gap-3 mt-3 pt-3 border-t border-[var(--color-border)]">
          <ComplexityBadge label="Time" value={problem.analysis.time_complexity} />
          <ComplexityBadge label="Space" value={problem.analysis.space_complexity} />
        </div>
      ) : null}
    </button>
  );
}

function ComplexityBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[12px]">
      <span className="text-[var(--color-text-3)]">{label}:</span>
      <code className="font-mono font-semibold text-violet-600 dark:text-violet-400">{value}</code>
    </span>
  );
}
