"use client";

import {
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import {
  useCreateTopic,
  useDeleteSubsection,
  useUpdateSubsection,
} from "@/hooks/useStudy";
import type { StudyKind, StudyPlanSubsection } from "@/lib/types";

import { AIGenerateTopicsModal } from "./AIGenerateModal";
import { StudyProgressBar } from "./StudyProgressBar";
import { TopicRow } from "./TopicRow";

export function SubsectionCard({
  subsection,
  sectionName,
}: {
  subsection: StudyPlanSubsection;
  sectionName: string;
}) {
  const update = useUpdateSubsection();
  const remove = useDeleteSubsection();
  const createTopic = useCreateTopic();

  const [collapsed, setCollapsed] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draftName, setDraftName] = useState(subsection.name);
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newKind, setNewKind] = useState<StudyKind>("learn");
  const [menuOpen, setMenuOpen] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);

  const total = subsection.topics.length;
  const done = subsection.topics.filter(
    (t) => t.status === "done" || t.status === "mastered",
  ).length;

  const commitRename = async () => {
    const trimmed = draftName.trim();
    if (!trimmed || trimmed === subsection.name) {
      setRenaming(false);
      setDraftName(subsection.name);
      return;
    }
    try {
      await update.mutateAsync({
        id: subsection.id,
        patch: { name: trimmed },
      });
    } finally {
      setRenaming(false);
    }
  };

  const submitTopic = async () => {
    const title = newTitle.trim();
    if (!title) {
      setAdding(false);
      setNewTitle("");
      return;
    }
    try {
      await createTopic.mutateAsync({
        subsectionId: subsection.id,
        data: { title, kind: newKind },
      });
    } finally {
      setNewTitle("");
      // Stay in adding mode so the user can chain — common Notion pattern.
    }
  };

  return (
    <>
    {showAIModal && (
      <AIGenerateTopicsModal
        subsectionId={subsection.id}
        subsectionName={subsection.name}
        sectionName={sectionName}
        onClose={() => setShowAIModal(false)}
      />
    )}
    <section
      id={`sub-${subsection.id}`}
      className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] hover:ring-[var(--color-border-2)] transition-shadow shadow-sm"
    >
      <header className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)]">
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "Expand" : "Collapse"}
          className="shrink-0 p-1 text-[var(--color-text-3)] hover:text-[var(--color-text)] rounded transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
        {renaming ? (
          <input
            autoFocus
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitRename();
              if (e.key === "Escape") {
                setRenaming(false);
                setDraftName(subsection.name);
              }
            }}
            className="flex-1 bg-[var(--color-surface)] ring-1 ring-indigo-500 rounded px-2 py-1 text-[15px] font-semibold text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-500"
          />
        ) : (
          <h3
            onDoubleClick={() => setRenaming(true)}
            className="flex-1 min-w-0 text-[15px] font-semibold text-[var(--color-text)] truncate cursor-text"
            title="Double-click to rename"
          >
            {subsection.name}
          </h3>
        )}
        <div className="hidden sm:block w-40 shrink-0">
          {total > 0 ? (
            <StudyProgressBar done={done} total={total} />
          ) : (
            <span className="text-[11px] text-[var(--color-text-3)]">no topics yet</span>
          )}
        </div>
        <div className="relative shrink-0">
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="p-1 rounded text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
            aria-label="Subsection options"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>
          {menuOpen ? (
            <div className="absolute right-0 top-8 z-20 w-44 rounded-lg bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-lg py-1 fade-up">
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  setRenaming(true);
                }}
                className="w-full text-left px-3 py-1.5 text-[12.5px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  if (
                    confirm(
                      `Delete "${subsection.name}" and its ${total} topics from ${sectionName}?`,
                    )
                  ) {
                    remove.mutate(subsection.id);
                  }
                }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-[12.5px] text-rose-700 hover:bg-rose-50"
              >
                <Trash2 className="w-3 h-3" />
                Delete subsection
              </button>
            </div>
          ) : null}
        </div>
      </header>

      {!collapsed ? (
        <div className="px-2 py-1">
          {subsection.topics.length === 0 && !adding ? (
            <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-text-3)]">
              No topics yet. Add one below.
            </p>
          ) : (
            <ul>
              {subsection.topics.map((t) => (
                <TopicRow key={t.id} topic={t} />
              ))}
            </ul>
          )}

          <div className="flex items-center gap-1 mt-1">
            <button
              type="button"
              onClick={() => setShowAIModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11.5px] text-violet-400 hover:text-violet-300 hover:bg-violet-500/10 rounded-lg transition-colors"
            >
              <Sparkles className="w-3 h-3" />
              AI suggest
            </button>
          </div>

          {adding ? (
            <div className="mx-2 my-1 px-3 py-2 rounded-lg ring-2 ring-indigo-500 bg-indigo-500/5 flex items-center gap-2">
              <KindToggle value={newKind} onChange={setNewKind} compact />
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onBlur={() => {
                  if (newTitle.trim()) {
                    submitTopic();
                  } else {
                    setAdding(false);
                    setNewTitle("");
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    submitTopic();
                  }
                  if (e.key === "Escape") {
                    setAdding(false);
                    setNewTitle("");
                  }
                }}
                placeholder="Topic title — Enter to add, Esc to close"
                className="flex-1 bg-transparent text-[13.5px] text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-3)]"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="w-full px-4 py-2 mt-1 mx-0 flex items-center gap-2 text-[12.5px] text-[var(--color-text-3)] hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Add topic
            </button>
          )}
        </div>
      ) : null}
    </section>
    </>
  );
}

/**
 * Tiny two-state segmented control for "Learn" vs "Revise". Compact
 * variant fits inside the inline-add row; the wider one is used inside
 * the topic edit panel.
 */
export function KindToggle({
  value,
  onChange,
  compact = false,
}: {
  value: StudyKind;
  onChange: (v: StudyKind) => void;
  compact?: boolean;
}) {
  const base = compact
    ? "text-[10.5px] px-2 py-0.5"
    : "text-[11.5px] px-2.5 py-1";
  return (
    <div
      role="radiogroup"
      aria-label="Topic kind"
      className="inline-flex rounded-full bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] shrink-0"
    >
      {(["learn", "revise"] as const).map((k) => (
        <button
          key={k}
          type="button"
          role="radio"
          aria-checked={value === k}
          onClick={() => onChange(k)}
          className={`${base} font-medium rounded-full transition-colors ${
            value === k
              ? k === "learn"
                ? "bg-sky-500 text-white"
                : "bg-violet-500 text-white"
              : "text-[var(--color-text-3)] hover:text-[var(--color-text)]"
          }`}
        >
          {k === "learn" ? "Learn" : "Revise"}
        </button>
      ))}
    </div>
  );
}
