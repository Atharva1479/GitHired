"use client";
import { useState } from "react";
import { Bookmark, BookmarkCheck, Clock, ExternalLink, MapPin } from "lucide-react";

import { useMatchResume } from "@/hooks/useJobs";
import type { FreshnessColor, JobResult } from "@/types/jobs";

interface JobCardProps {
  job: JobResult;
  onApply: (job: JobResult) => void;
  onBookmark: (job: JobResult) => void;
  onPreview: (job: JobResult) => void;
}

const COLOR_MAP: Record<FreshnessColor, { bg: string; text: string; ring: string }> = {
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-600", ring: "ring-emerald-500/20" },
  green:   { bg: "bg-green-500/10",   text: "text-green-600",   ring: "ring-green-500/20" },
  amber:   { bg: "bg-amber-500/10",   text: "text-amber-600",   ring: "ring-amber-500/20" },
  orange:  { bg: "bg-orange-500/10",  text: "text-orange-600",  ring: "ring-orange-500/20" },
  red:     { bg: "bg-red-500/10",     text: "text-red-600",     ring: "ring-red-500/20" },
  zinc:    { bg: "bg-zinc-500/10",    text: "text-zinc-500",    ring: "ring-zinc-500/20" },
};

function MatchChip({ jobId }: { jobId: number }) {
  const { data, isLoading } = useMatchResume(jobId);
  if (isLoading) return <span className="text-xs text-[var(--color-text-3)] animate-pulse">Scanning…</span>;
  if (!data || data.score === null) return null;
  const s = data.score;
  const cls = s >= 75 ? "text-emerald-600" : s >= 55 ? "text-amber-600" : "text-red-500";
  return <span className={`text-xs font-semibold ${cls}`}>{s}% match</span>;
}

function CompetitionBar({ score }: { score: number }) {
  const color =
    score >= 75 ? "bg-emerald-500" :
    score >= 50 ? "bg-green-500" :
    score >= 30 ? "bg-amber-500" :
    "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-[var(--color-text-3)] shrink-0 w-24">Low competition</span>
      <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)]">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-[var(--color-text-3)] shrink-0">High</span>
    </div>
  );
}

function timeAgo(posted_at: string | null): string {
  if (!posted_at) return "Unknown";
  const hours = (Date.now() - new Date(posted_at).getTime()) / 36e5;
  if (hours < 1) return `${Math.round(hours * 60)}m ago`;
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function JobCard({ job, onApply, onBookmark, onPreview }: JobCardProps) {
  const [bookmarked, setBookmarked] = useState(
    job.bookmark_status === "bookmarked" || job.bookmark_status === "applied",
  );
  const applied = job.bookmark_status === "applied";
  const colors = COLOR_MAP[job.freshness_color] ?? COLOR_MAP.zinc;

  function handleBookmark(e: React.MouseEvent) {
    e.stopPropagation();
    setBookmarked(true);
    onBookmark(job);
  }

  return (
    <div
      onClick={() => onPreview(job)}
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 flex flex-col gap-3 hover:border-indigo-400/60 transition-colors cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ring-1 ${colors.bg} ${colors.text} ${colors.ring}`}>
              {job.freshness_label}
            </span>
            {applied && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-500 ring-1 ring-indigo-500/20">
                ✓ Applied
              </span>
            )}
            <MatchChip jobId={job.id} />
          </div>
          <h3 className="font-semibold text-[var(--color-text)] text-sm leading-snug line-clamp-2">{job.title}</h3>
          <p className="text-sm text-[var(--color-text-2)] mt-0.5">{job.company}</p>
        </div>
        <button
          onClick={handleBookmark}
          className="shrink-0 p-1.5 rounded-lg hover:bg-[var(--color-border)] transition-colors"
          title={bookmarked ? "Bookmarked" : "Bookmark"}
        >
          {bookmarked
            ? <BookmarkCheck className="w-4 h-4 text-indigo-500" />
            : <Bookmark className="w-4 h-4 text-[var(--color-text-3)]" />}
        </button>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs text-[var(--color-text-3)] flex-wrap">
        {job.location && (
          <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>
        )}
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{timeAgo(job.posted_at)}</span>
        {job.employment_type && (
          <span className="px-2 py-0.5 rounded bg-[var(--color-border)] capitalize">
            {job.employment_type.replace(/_/g, " ").toLowerCase()}
          </span>
        )}
      </div>

      {/* Competition bar */}
      <CompetitionBar score={job.freshness_score} />

      <p className="text-xs text-[var(--color-text-3)]">
        Est. applicants: <span className={`font-semibold ${colors.text}`}>{job.est_applicants}</span>
      </p>

      {/* Skills */}
      {job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {job.skills.slice(0, 6).map((s) => (
            <span key={s} className="px-2 py-0.5 rounded-md text-xs bg-[var(--color-border)] text-[var(--color-text-2)]">
              {s}
            </span>
          ))}
          {job.skills.length > 6 && (
            <span className="px-2 py-0.5 text-xs text-[var(--color-text-3)]">+{job.skills.length - 6} more</span>
          )}
        </div>
      )}

      {/* CTA */}
      <div className="flex gap-2 pt-1" onClick={(e) => e.stopPropagation()}>
        {applied ? (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-[var(--color-border)] text-sm font-medium hover:border-indigo-400 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> View Posting
          </a>
        ) : (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onApply(job); }}
              className="flex-1 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 transition-colors"
            >
              Apply & Track
            </button>
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-2 rounded-lg border border-[var(--color-border)] hover:border-indigo-400 transition-colors"
              title="Open posting"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="w-4 h-4 text-[var(--color-text-3)]" />
            </a>
          </>
        )}
      </div>
    </div>
  );
}
