"use client";
import { useState, useEffect } from "react";
import { Briefcase, TrendingUp, Zap } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import ApplyModal from "@/components/jobs/ApplyModal";
import JobCard from "@/components/jobs/JobCard";
import JobFilters from "@/components/jobs/JobFilters";
import JobPreviewPanel from "@/components/jobs/JobPreviewPanel";
import SavedSearchPanel from "@/components/jobs/SavedSearchPanel";
import { useBookmarkJob, useJobSearch } from "@/hooks/useJobs";
import type { JobResult, SearchParams } from "@/types/jobs";

const SEARCH_SOURCES = [
  "Searching JSearch…",
  "Querying Adzuna…",
  "Checking Arbeitnow…",
  "Scanning ATS boards…",
  "Filtering & ranking…",
];

function SearchProgress() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % SEARCH_SOURCES.length), 2200);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="w-48 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
        <div className="h-full bg-indigo-500 rounded-full animate-[progress_2.2s_ease-in-out_infinite]" />
      </div>
      <p className="text-sm text-[var(--color-text-3)] animate-pulse">{SEARCH_SOURCES[step]}</p>
      <p className="text-xs text-[var(--color-text-3)]">Aggregating fresh jobs from multiple sources…</p>
    </div>
  );
}

export default function JobsPage() {
  const _SEARCH_KEY = "jp_job_search";

  const [searchParams, setSearchParams] = useState<SearchParams | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = sessionStorage.getItem(_SEARCH_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as { params: SearchParams; freshness: number };
      return parsed.params ?? null;
    } catch {
      return null;
    }
  });
  const [freshnessHours, setFreshnessHours] = useState<number>(() => {
    if (typeof window === "undefined") return 72;
    try {
      const raw = sessionStorage.getItem(_SEARCH_KEY);
      if (!raw) return 72;
      const parsed = JSON.parse(raw) as { params: SearchParams; freshness: number };
      return parsed.freshness ?? 72;
    } catch {
      return 72;
    }
  });
  const [applyJob, setApplyJob]             = useState<JobResult | null>(null);
  const [previewJob, setPreviewJob]         = useState<JobResult | null>(null);
  const [appliedCount, setAppliedCount]     = useState(0);

  useEffect(() => {
    if (!searchParams) return;
    try {
      sessionStorage.setItem(_SEARCH_KEY, JSON.stringify({ params: searchParams, freshness: freshnessHours }));
    } catch {
      // storage unavailable — ignore
    }
  }, [searchParams, freshnessHours]);

  const { data: allJobs, filteredData: jobs, isLoading, error } = useJobSearch(searchParams, freshnessHours);
  const { mutate: bookmarkJob } = useBookmarkJob();

  function handleApply(job: JobResult) {
    setPreviewJob(null);
    setApplyJob(job);
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Hero */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
              <Zap className="w-5 h-5 text-indigo-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[var(--color-text)]">Fresh Job Finder</h1>
              <p className="text-sm text-[var(--color-text-3)]">
                Apply within 6–24 h of posting — before 100 applicants pile up
              </p>
            </div>
          </div>
          <div className="flex gap-3 flex-wrap">
            {[
              { dot: "bg-emerald-500", label: "🔥 < 6h · ~5–30 applicants" },
              { dot: "bg-green-500",   label: "⚡ 6–24h · ~30–150 applicants" },
              { dot: "bg-red-500",     label: "🔴 72h+ · 700+ applicants" },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-xs">
                <span className={`w-2 h-2 rounded-full ${b.dot}`} />
                <span className="text-[var(--color-text-2)]">{b.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 mb-4">
          <JobFilters
            onSearch={setSearchParams}
            onFreshnessChange={setFreshnessHours}
            isLoading={isLoading}
          />
        </div>

        {/* Saved searches */}
        <div className="mb-6">
          <SavedSearchPanel currentParams={searchParams} onLoad={setSearchParams} />
        </div>

        {/* States */}
        {!searchParams && (
          <div className="text-center py-20">
            <Briefcase className="w-10 h-10 mx-auto mb-3 text-[var(--color-text-3)]" />
            <p className="font-medium text-[var(--color-text-2)]">Search for a role to discover fresh jobs</p>
            <p className="text-sm text-[var(--color-text-3)] mt-1">
              Try "Java Backend Engineer", "Python FastAPI", "Agentic AI Developer"
            </p>
          </div>
        )}

        {isLoading && <SearchProgress />}

        {error && (
          <div className="rounded-xl bg-red-500/10 ring-1 ring-red-500/20 px-4 py-3 text-sm text-red-600">
            {(error as Error).message}
          </div>
        )}

        {/* No API results */}
        {allJobs && allJobs.length === 0 && searchParams && !isLoading && (
          <div className="text-center py-16">
            <TrendingUp className="w-8 h-8 mx-auto mb-3 text-[var(--color-text-3)]" />
            <p className="font-medium text-[var(--color-text-2)]">No jobs found in the last 3 days</p>
            <p className="text-sm text-[var(--color-text-3)] mt-1">
              Try a broader keyword or different location
            </p>
          </div>
        )}

        {/* Freshness filter is too narrow */}
        {allJobs && allJobs.length > 0 && jobs.length === 0 && !isLoading && (
          <div className="text-center py-16">
            <TrendingUp className="w-8 h-8 mx-auto mb-3 text-[var(--color-text-3)]" />
            <p className="font-medium text-[var(--color-text-2)]">No jobs in this time window</p>
            <p className="text-sm text-[var(--color-text-3)] mt-1">
              {allJobs.length} jobs found — try &quot;Last 3 days&quot; to see them all
            </p>
          </div>
        )}

        {jobs.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-[var(--color-text-3)]">
                <span className="font-semibold text-[var(--color-text)]">{jobs.length}</span>
                {allJobs && allJobs.length > jobs.length && (
                  <span> / {allJobs.length}</span>
                )}
                {" "}jobs · sorted by lowest competition
              </p>
              {appliedCount > 0 && (
                <span className="text-xs text-emerald-600 font-medium">✓ {appliedCount} applied this session</span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {jobs.map((job) => (
                <JobCard
                  key={`${job.source}-${job.external_id}`}
                  job={job}
                  onApply={handleApply}
                  onPreview={setPreviewJob}
                  onBookmark={(j) => bookmarkJob(j.id)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {previewJob && (
        <JobPreviewPanel
          job={previewJob}
          onClose={() => setPreviewJob(null)}
          onApply={handleApply}
        />
      )}

      {applyJob && (
        <ApplyModal
          job={applyJob}
          onClose={() => setApplyJob(null)}
          onSuccess={() => setAppliedCount((c) => c + 1)}
          onViewJob={(similar) => { setApplyJob(null); setPreviewJob(similar); }}
        />
      )}
    </AppShell>
  );
}
