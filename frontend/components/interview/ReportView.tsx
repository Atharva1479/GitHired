"use client";
import { Loader2, Trophy } from "lucide-react";
import Link from "next/link";

import { useReport } from "@/hooks/useInterview";

function ScoreDisplay({ score }: { score: number }) {
  const color =
    score >= 70 ? "text-emerald-500" : score >= 50 ? "text-amber-500" : "text-red-500";
  return (
    <div className={`text-5xl font-bold ${color}`}>
      {score}
      <span className="text-lg text-[var(--color-text-2)]">/100</span>
    </div>
  );
}

export default function ReportView({ sessionId }: { sessionId: number }) {
  const { data, isLoading } = useReport(sessionId);

  if (isLoading || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        <p className="text-sm text-[var(--color-text-2)]">Loading report…</p>
      </div>
    );
  }

  if (data.status === "pending") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        <p className="text-sm text-[var(--color-text-2)]">AI is evaluating your answers…</p>
        <p className="text-xs text-[var(--color-text-3)]">This takes about 30–60 seconds</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 mb-2">
          <Trophy className="w-7 h-7 text-indigo-500" />
        </div>
        <h1 className="text-2xl font-bold">Interview Complete</h1>
        {data.session && (
          <p className="text-sm text-[var(--color-text-2)]">
            {data.session.role} · {data.session.topic} · {data.session.duration_min} min
          </p>
        )}
      </div>

      {/* Score hero */}
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 flex items-center gap-6">
        <div className="flex flex-col items-center shrink-0 min-w-[96px]">
          <ScoreDisplay score={data.overall_score ?? 0} />
          <p className="text-xs text-[var(--color-text-3)] mt-1">Overall Score</p>
        </div>
        {data.summary && (
          <div className="border-l border-[var(--color-border)] pl-6">
            <p className="text-xs font-semibold text-[var(--color-text-3)] uppercase tracking-wide mb-1">Summary</p>
            <p className="text-sm text-[var(--color-text-2)] leading-relaxed">{data.summary}</p>
          </div>
        )}
      </div>

      {/* Skill breakdown */}
      {data.skill_breakdown && Object.keys(data.skill_breakdown).length > 0 && (
        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4">
          <h2 className="font-semibold text-sm">Skill Breakdown</h2>
          {Object.entries(data.skill_breakdown).map(([skill, score]) => (
            <div key={skill} className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span>{skill}</span>
                <span className="font-medium tabular-nums">{score}/100</span>
              </div>
              <div className="h-1.5 rounded-full bg-[var(--color-border)]">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Per-question breakdown */}
      {data.questions && data.questions.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-semibold text-sm">Question Breakdown</h2>
          {data.questions.map((q) => {
            const scoreColor =
              q.score >= 7 ? "text-emerald-500" : q.score >= 5 ? "text-amber-500" : "text-red-500";
            return (
              <div
                key={q.question_index}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-3"
              >
                <div className="flex items-start justify-between gap-4">
                  <p className="font-medium text-sm">
                    Q{q.question_index + 1}: {q.question}
                  </p>
                  <span className={`text-sm font-bold shrink-0 tabular-nums ${scoreColor}`}>
                    {q.score}/10
                  </span>
                </div>
                <p className="text-sm text-[var(--color-text-2)]">
                  <span className="font-medium text-[var(--color-text)]">Your answer: </span>
                  {q.user_answer || <em className="text-[var(--color-text-3)]">No answer recorded</em>}
                </p>
                <div className="rounded-lg bg-emerald-500/5 ring-1 ring-emerald-300/20 p-3 text-sm">
                  <p className="font-medium text-emerald-600 dark:text-emerald-400 mb-1 text-xs uppercase tracking-wide">
                    Ideal Answer
                  </p>
                  <p className="text-[var(--color-text-2)] leading-relaxed">{q.ideal_answer}</p>
                </div>
                <p className="text-sm text-[var(--color-text-2)]">
                  <span className="font-medium text-[var(--color-text)]">Feedback: </span>
                  {q.feedback}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 justify-center pb-4">
        <Link
          href="/interview"
          className="px-6 py-2.5 rounded-lg bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-700 transition-colors"
        >
          Practice Again
        </Link>
        <Link
          href="/interview/history"
          className="px-6 py-2.5 rounded-lg border border-[var(--color-border)] text-sm font-medium hover:border-indigo-400 transition-colors"
        >
          View History
        </Link>
      </div>
    </div>
  );
}
