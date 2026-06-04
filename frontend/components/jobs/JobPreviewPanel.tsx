"use client";
import { useEffect } from "react";
import { Clock, ExternalLink, MapPin, X, Zap } from "lucide-react";

import { useMatchResume } from "@/hooks/useJobs";
import type { JobResult } from "@/types/jobs";

interface JobPreviewPanelProps {
  job: JobResult;
  onClose: () => void;
  onApply: (job: JobResult) => void;
}

function MatchBadge({ jobId }: { jobId: number }) {
  const { data, isLoading } = useMatchResume(jobId);

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-border)] text-[var(--color-text-3)] animate-pulse">
        Scanning…
      </span>
    );
  }
  if (!data || data.score === null) return null;

  const score = data.score;
  const color =
    score >= 75 ? "bg-emerald-500/10 text-emerald-600 ring-emerald-500/20" :
    score >= 55 ? "bg-amber-500/10 text-amber-600 ring-amber-500/20" :
    "bg-red-500/10 text-red-600 ring-red-500/20";

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ring-1 ${color}`}>
      {score}% resume match
    </span>
  );
}

function timeAgo(posted_at: string | null): string {
  if (!posted_at) return "Unknown";
  const hours = (Date.now() - new Date(posted_at).getTime()) / 36e5;
  if (hours < 1) return `${Math.round(hours * 60)}m ago`;
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function JobPreviewPanel({ job, onClose, onApply }: JobPreviewPanelProps) {
  const applied = job.bookmark_status === "applied";

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg flex flex-col bg-[var(--color-bg)] border-l border-[var(--color-border)] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-6 py-5 border-b border-[var(--color-border)]">
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-base text-[var(--color-text)] leading-snug">{job.title}</h2>
            <p className="text-sm text-[var(--color-text-2)] mt-0.5">{job.company}</p>
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              {job.location && (
                <span className="flex items-center gap-1 text-xs text-[var(--color-text-3)]">
                  <MapPin className="w-3 h-3" />{job.location}
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-[var(--color-text-3)]">
                <Clock className="w-3 h-3" />{timeAgo(job.posted_at)}
              </span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full
                ${job.freshness_color === "emerald" ? "bg-emerald-500/10 text-emerald-600" :
                  job.freshness_color === "green"   ? "bg-green-500/10 text-green-600" :
                  job.freshness_color === "amber"   ? "bg-amber-500/10 text-amber-600" :
                  "bg-red-500/10 text-red-600"}`}>
                {job.freshness_label}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 p-1.5 rounded-lg hover:bg-[var(--color-border)] transition-colors"
          >
            <X className="w-4 h-4 text-[var(--color-text-3)]" />
          </button>
        </div>

        {/* Resume match + competition */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-[var(--color-border)] flex-wrap">
          <MatchBadge jobId={job.id} />
          <span className="text-xs text-[var(--color-text-3)]">
            Est. <span className="font-semibold text-[var(--color-text-2)]">{job.est_applicants}</span> applicants
          </span>
          {job.skills.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {job.skills.slice(0, 5).map((s) => (
                <span key={s} className="px-2 py-0.5 rounded text-xs bg-[var(--color-border)] text-[var(--color-text-2)]">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* JD body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {job.description ? (
            <div className="text-sm text-[var(--color-text-2)] leading-relaxed whitespace-pre-wrap">
              {job.description}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-sm text-[var(--color-text-3)]">No description available</p>
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-sm text-indigo-500 hover:underline"
              >
                View on job site <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>

        {/* Footer CTAs */}
        <div className="px-6 py-4 border-t border-[var(--color-border)] flex gap-3">
          {applied ? (
            <>
              <span className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-[var(--color-border)] text-sm text-indigo-500 font-medium">
                ✓ Applied
              </span>
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl border border-[var(--color-border)] hover:border-indigo-400 transition-colors"
                title="View posting"
              >
                <ExternalLink className="w-4 h-4 text-[var(--color-text-3)]" />
              </a>
            </>
          ) : (
            <>
              <button
                onClick={() => onApply(job)}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 transition-colors"
              >
                <Zap className="w-4 h-4" />
                Apply & Track
              </button>
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl border border-[var(--color-border)] hover:border-indigo-400 transition-colors"
                title="Open on job site"
              >
                <ExternalLink className="w-4 h-4 text-[var(--color-text-3)]" />
              </a>
            </>
          )}
        </div>
      </div>
    </>
  );
}
