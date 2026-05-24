"use client";

interface Props {
  suggestions: string[];
}

function borderColor(text: string) {
  if (text.startsWith("Critical:") || text.startsWith("ATS Risk")) return "border-red-500";
  if (text.startsWith("Word2Vec")) return "border-violet-500";
  return "border-amber-500";
}

function labelBadge(text: string) {
  if (text.startsWith("Critical:") || text.startsWith("ATS Risk")) {
    return <span className="text-[10px] font-semibold uppercase tracking-wider text-red-500">Critical</span>;
  }
  if (text.startsWith("Word2Vec")) {
    return <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-500">Semantic</span>;
  }
  return <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-600">Advisory</span>;
}

export function Suggestions({ suggestions }: Props) {
  if (suggestions.length === 0) {
    return (
      <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
        <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-2">Suggestions</h2>
        <p className="text-[13px] text-emerald-500 font-medium">No suggestions — your resume looks great!</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
      <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-4">
        Improvement Suggestions
      </h2>
      <ol className="space-y-3">
        {suggestions.map((s, i) => (
          <li
            key={i}
            className={`flex gap-3 rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] border-l-4 px-4 py-3 ${borderColor(s)}`}
          >
            <span className="shrink-0 w-6 h-6 rounded-full bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] flex items-center justify-center text-[11px] font-semibold text-[var(--color-text-2)] mt-0.5">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="mb-0.5">{labelBadge(s)}</div>
              <p className="text-[13px] text-[var(--color-text)]">{s}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
