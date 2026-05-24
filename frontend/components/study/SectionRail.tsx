"use client";

import {
  Check,
  ChevronDown,
  ChevronRight,
  Home,
  MoreHorizontal,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import {
  useCreateSection,
  useDeleteSection,
  useUpdateSection,
} from "@/hooks/useStudy";
import type { StudyPlanSection } from "@/lib/types";

type Props = {
  sections: StudyPlanSection[];
  activeSectionId: number | null;
  onSelect: (id: number) => void;
  onHome: () => void;
};

export function SectionRail({
  sections,
  activeSectionId,
  onSelect,
  onHome,
}: Props) {
  const create = useCreateSection();
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");

  const submitNew = async () => {
    const trimmed = newName.trim();
    if (!trimmed) {
      setAdding(false);
      setNewName("");
      return;
    }
    try {
      await create.mutateAsync({ name: trimmed });
    } finally {
      setAdding(false);
      setNewName("");
    }
  };

  return (
    <aside className="w-[240px] shrink-0">
      {/* Home button */}
      <button
        type="button"
        onClick={onHome}
        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md mb-2 text-[13.5px] font-medium transition-colors ${
          activeSectionId === null
            ? "bg-indigo-500/10 text-indigo-400"
            : "text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)]"
        }`}
      >
        <Home className="w-3.5 h-3.5 shrink-0" />
        Home
      </button>

      <div className="flex items-center justify-between mb-2 px-2">
        <h2 className="text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-text-3)] font-semibold">
          Study plan
        </h2>
        <button
          type="button"
          onClick={() => setAdding(true)}
          aria-label="Add section"
          className="p-1 rounded-md text-[var(--color-text-3)] hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
      <ul className="space-y-0.5">
        {sections.map((s) => (
          <SectionRow
            key={s.id}
            section={s}
            active={s.id === activeSectionId}
            onSelect={() => onSelect(s.id)}
          />
        ))}
        {adding ? (
          <li className="px-2 py-1.5">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onBlur={submitNew}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitNew();
                if (e.key === "Escape") {
                  setAdding(false);
                  setNewName("");
                }
              }}
              placeholder="Section name…"
              className="w-full bg-[var(--color-surface)] ring-1 ring-indigo-500 rounded-md px-2.5 py-1.5 text-[13.5px] text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </li>
        ) : null}
      </ul>
    </aside>
  );
}

function SectionRow({
  section,
  active,
  onSelect,
}: {
  section: StudyPlanSection;
  active: boolean;
  onSelect: () => void;
}) {
  const update = useUpdateSection();
  const remove = useDeleteSection();
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(section.name);
  const [menuOpen, setMenuOpen] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const totalTopics = section.subsections.reduce(
    (n, sub) => n + sub.topics.length,
    0,
  );
  const doneTopics = section.subsections.reduce(
    (n, sub) =>
      n + sub.topics.filter((t) => t.status === "done" || t.status === "mastered").length,
    0,
  );

  const commitRename = async () => {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === section.name) {
      setRenaming(false);
      setDraft(section.name);
      return;
    }
    try {
      await update.mutateAsync({ id: section.id, patch: { name: trimmed } });
    } finally {
      setRenaming(false);
    }
  };

  return (
    <li>
      <div
        className={`group/sec flex items-center gap-1 px-2 py-1.5 rounded-md transition-colors cursor-pointer ${
          active
            ? "bg-indigo-500/10 text-indigo-400"
            : "text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
        }`}
        onClick={() => {
          if (renaming) return;
          onSelect();
        }}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
          className="shrink-0 p-0.5 text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </button>
        {renaming ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitRename}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitRename();
              if (e.key === "Escape") {
                setRenaming(false);
                setDraft(section.name);
              }
            }}
            className="flex-1 bg-[var(--color-surface)] ring-1 ring-indigo-500 rounded px-2 py-0.5 text-[13.5px] text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-500"
          />
        ) : (
          <button
            type="button"
            onDoubleClick={(e) => {
              e.stopPropagation();
              setRenaming(true);
            }}
            className="flex-1 min-w-0 text-left text-[13.5px] font-medium truncate"
          >
            {section.name}
          </button>
        )}
        <span className="shrink-0 text-[10.5px] tabular-nums text-[var(--color-text-3)]">
          {totalTopics > 0 ? `${doneTopics}/${totalTopics}` : ""}
        </span>
        <div className="relative">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen((v) => !v);
            }}
            aria-label="Section options"
            className="shrink-0 p-0.5 rounded text-[var(--color-text-3)] opacity-0 group-hover/sec:opacity-100 hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text-2)] transition-opacity"
          >
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>
          {menuOpen ? (
            <div
              className="absolute right-0 top-6 z-20 w-40 rounded-lg bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-lg py-1 fade-up"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  setRenaming(true);
                }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-[12.5px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
              >
                <Check className="w-3 h-3" />
                Rename
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  if (
                    confirm(
                      `Delete "${section.name}" and its ${totalTopics} topics?`,
                    )
                  ) {
                    remove.mutate(section.id);
                  }
                }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-[12.5px] text-rose-700 hover:bg-rose-50"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          ) : null}
        </div>
      </div>
      {expanded && section.subsections.length > 0 ? (
        <ul className="ml-5 mt-0.5 mb-1 space-y-0.5">
          {section.subsections.map((sub) => {
            const subDone = sub.topics.filter(
              (t) => t.status === "done" || t.status === "mastered",
            ).length;
            return (
              <li
                key={sub.id}
                className="flex items-center gap-2 px-2 py-1 text-[12.5px] text-[var(--color-text-2)] hover:text-[var(--color-text)] cursor-pointer rounded-md hover:bg-[var(--color-surface-2)]"
                onClick={() => {
                  onSelect();
                  document
                    .getElementById(`sub-${sub.id}`)
                    ?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                <span className="truncate flex-1">{sub.name}</span>
                <span className="shrink-0 text-[10.5px] tabular-nums text-[var(--color-text-3)]">
                  {subDone}/{sub.topics.length}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
    </li>
  );
}
