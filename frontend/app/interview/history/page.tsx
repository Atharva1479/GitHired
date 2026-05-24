"use client";
import { ChevronRight, Mic } from "lucide-react";
import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { useHistory } from "@/hooks/useInterview";

export default function InterviewHistoryPage() {
  const { data: sessions, isLoading } = useHistory();

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold">Interview History</h1>
          <Link
            href="/interview"
            className="text-sm text-indigo-500 hover:underline"
          >
            New Interview →
          </Link>
        </div>

        {isLoading && (
          <p className="text-sm text-[var(--color-text-2)]">Loading…</p>
        )}

        {!isLoading && sessions?.length === 0 && (
          <div className="text-center py-20">
            <Mic className="w-8 h-8 mx-auto mb-3 text-[var(--color-text-3)]" />
            <p className="text-sm text-[var(--color-text-2)]">No interviews yet.</p>
            <Link
              href="/interview"
              className="mt-4 inline-block text-indigo-500 text-sm hover:underline"
            >
              Start your first interview →
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {sessions?.map((s) => (
            <Link
              key={s.id}
              href={`/interview/report/${s.id}`}
              className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 hover:border-indigo-400 transition-colors"
            >
              <div>
                <p className="font-medium text-sm">
                  {s.topic} — {s.role}
                </p>
                <p className="text-xs text-[var(--color-text-2)] mt-0.5">
                  {s.years_exp} yrs exp · {s.duration_min} min ·{" "}
                  {new Date(s.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    s.status === "ended"
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {s.status}
                </span>
                <ChevronRight className="w-4 h-4 text-[var(--color-text-3)]" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
