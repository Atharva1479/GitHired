"use client";
import { useState } from "react";
import { Search } from "lucide-react";

import type { SearchParams } from "@/types/jobs";

interface JobFiltersProps {
  onSearch: (params: SearchParams) => void;
  isLoading: boolean;
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

export default function JobFilters({ onSearch, isLoading }: JobFiltersProps) {
  const [query, setQuery]         = useState("");
  const [location, setLocation]   = useState("");
  const [experience, setExp]      = useState("");
  const [freshness, setFreshness] = useState(24);
  const [remoteOnly, setRemote]   = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    onSearch({
      q: query.trim(),
      location: location.trim() || undefined,
      experience: experience || undefined,
      freshness_hours: freshness,
      remote_only: remoteOnly,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
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
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? "Searching…" : "Search"}
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {/* Freshness pills */}
        <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-1">
          {FRESHNESS_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setFreshness(o.value)}
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
    </form>
  );
}
