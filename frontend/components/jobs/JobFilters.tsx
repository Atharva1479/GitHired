"use client";
import { useState } from "react";
import { Search } from "lucide-react";

import type { SearchParams } from "@/types/jobs";

interface ResumeOption {
  id: number;
  name: string;
  role_tag: string;
}

interface JobFiltersProps {
  onSearch: (params: SearchParams) => void;
  onFreshnessChange?: (hours: number) => void;
  isLoading: boolean;
  resumes?: ResumeOption[];
  selectedResumeId?: number | null;
  onResumeChange?: (id: number | null) => void;
}

const EXP_OPTIONS = [
  { value: "", label: "Any level" },
  { value: "entry", label: "Entry" },
  { value: "mid", label: "Mid" },
  { value: "senior", label: "Senior" },
];

const FRESHNESS_OPTIONS = [
  { value: 6,   label: "Last 6h" },
  { value: 24,  label: "Last 24h" },
  { value: 48,  label: "Last 2 days" },
  { value: 72,  label: "Last 3 days" },
  { value: 168, label: "Last week" },
];

const JOB_TYPES = [
  { value: "",         label: "All types" },
  { value: "full",     label: "Full-time" },
  { value: "part",     label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "intern",   label: "Internship" },
];

export default function JobFilters({
  onSearch,
  onFreshnessChange,
  isLoading,
  resumes = [],
  selectedResumeId = null,
  onResumeChange,
}: JobFiltersProps) {
  const [query, setQuery]         = useState("");
  const [location, setLocation]   = useState("");
  const [experience, setExp]      = useState("");
  const [freshness, setFreshness] = useState(72);
  const [remoteOnly, setRemote]   = useState(false);
  const [jobType, setJobType]     = useState("");

  function handleFreshnessChange(value: number) {
    setFreshness(value);
    onFreshnessChange?.(value);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    onSearch({
      q: query.trim(),
      location: location.trim() || undefined,
      experience: experience || undefined,
      remote_only: remoteOnly,
      employment_type: jobType || undefined,
      resume_id: selectedResumeId ?? undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Main search row */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-3)]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Role, skill, or keyword — e.g. Java Backend Engineer"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-sm placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location"
          className="w-36 px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-sm placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {resumes.length > 0 && (
          <select
            value={selectedResumeId ?? ""}
            onChange={(e) => onResumeChange?.(e.target.value ? Number(e.target.value) : null)}
            className="w-44 shrink-0 px-3 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-xs text-[var(--color-text-2)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
            title="Resume used for job matching"
          >
            <option value="">Auto-detect resume</option>
            {resumes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.role_tag})
              </option>
            ))}
          </select>
        )}
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? "Searching…" : "Search"}
        </button>
      </div>

      {/* Filter row 1: freshness + experience + remote */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Freshness pills */}
        <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-1">
          {FRESHNESS_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => handleFreshnessChange(o.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                freshness === o.value
                  ? "bg-indigo-600 text-white"
                  : "text-[var(--color-text-2)] hover:bg-[var(--color-border)]"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>

        <select
          value={experience}
          onChange={(e) => setExp(e.target.value)}
          className="px-3 py-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {EXP_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        {/* Remote toggle */}
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <button
            type="button"
            onClick={() => setRemote((v) => !v)}
            className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors ${remoteOnly ? "bg-indigo-600" : "bg-[var(--color-border)]"}`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${remoteOnly ? "translate-x-4" : "translate-x-0"}`} />
          </button>
          <span className="text-[var(--color-text-2)]">Remote only</span>
        </label>
      </div>

      {/* Filter row 2: job type chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-[var(--color-text-3)] font-medium">Type:</span>
        {JOB_TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setJobType(t.value)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              jobType === t.value
                ? "bg-indigo-600 border-indigo-600 text-white"
                : "border-[var(--color-border)] text-[var(--color-text-2)] hover:border-indigo-400"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </form>
  );
}
