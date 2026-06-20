"use client";
import { useState } from "react";
import { Bell, Plus, Trash2 } from "lucide-react";

import { useCreateSavedSearch, useDeleteSavedSearch, useNewJobsCount, useSavedSearches } from "@/hooks/useJobs";
import type { SearchParams } from "@/types/jobs";

interface SavedSearchPanelProps {
  currentParams: SearchParams | null;
  onLoad: (params: SearchParams) => void;
}

export default function SavedSearchPanel({ currentParams, onLoad }: SavedSearchPanelProps) {
  const { data: searches } = useSavedSearches();
  const { data: newCount } = useNewJobsCount();
  const { mutate: createSearch, isPending: creating } = useCreateSavedSearch();
  const { mutate: deleteSearch } = useDeleteSavedSearch();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");

  const totalNew = newCount?.total_new ?? 0;

  function handleSave() {
    if (!currentParams || !name.trim()) return;
    createSearch(
      {
        name: name.trim(),
        query: currentParams.q,
        location: currentParams.location,
        remote_only: currentParams.remote_only,
        experience: currentParams.experience,
      },
      { onSuccess: () => { setShowForm(false); setName(""); } },
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="relative shrink-0">
        <Bell className="w-4 h-4 text-[var(--color-text-3)]" />
        {totalNew > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-0.5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center leading-none">
            {totalNew > 99 ? "99+" : totalNew}
          </span>
        )}
      </div>
      <span className="text-xs text-[var(--color-text-3)] font-medium">
        Saved alerts:
        {totalNew > 0 && (
          <span className="ml-1 text-red-500 font-semibold">{totalNew} new</span>
        )}
      </span>

      {searches?.map((s) => (
        <div
          key={s.id}
          onClick={() => onLoad({ q: s.query, location: s.location ?? undefined, remote_only: s.remote_only, experience: s.experience ?? undefined })}
          className="group flex items-center gap-1 px-3 py-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] text-xs hover:border-indigo-400 transition-colors cursor-pointer"
        >
          {s.name}
          <button
            onClick={(e) => { e.stopPropagation(); deleteSearch(s.id); }}
            className="opacity-0 group-hover:opacity-100 ml-0.5 transition-opacity"
          >
            <Trash2 className="w-3 h-3 text-[var(--color-text-3)] hover:text-red-500" />
          </button>
        </div>
      ))}

      {currentParams?.q && !showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1 px-3 py-1 rounded-full border border-dashed border-[var(--color-border)] text-xs text-[var(--color-text-3)] hover:border-indigo-400 hover:text-indigo-500 transition-colors"
        >
          <Plus className="w-3 h-3" /> Save this search
        </button>
      )}

      {showForm && (
        <div className="flex items-center gap-2">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); if (e.key === "Escape") setShowForm(false); }}
            placeholder="Name this alert…"
            className="w-44 px-3 py-1 rounded-lg border border-indigo-400 bg-[var(--color-surface)] text-xs focus:outline-none"
          />
          <button onClick={handleSave} disabled={!name.trim() || creating} className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-medium disabled:opacity-50">
            Save
          </button>
          <button onClick={() => setShowForm(false)} className="text-xs text-[var(--color-text-3)]">
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
