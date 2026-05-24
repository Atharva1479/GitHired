"use client";

import {
  Check,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Sparkles,
  Tag,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";

import {
  useDeleteTopic,
  useReviseTopic,
  useUnmarkTopic,
  useUpdateTopic,
} from "@/hooks/useStudy";
import type { StudyKind, StudyStatus, StudyTopic } from "@/lib/types";

import { KindToggle } from "./SubsectionCard";

const _STATUS_DOT: Record<StudyStatus, string> = {
  todo: "bg-[var(--color-surface-2)]",
  in_progress: "bg-amber-400",
  done: "bg-emerald-500",
  mastered: "bg-gradient-to-br from-amber-400 to-fuchsia-500",
};

const _KIND_BADGE: Record<StudyKind, string> = {
  learn: "bg-sky-50 text-sky-700 ring-sky-200",
  revise: "bg-violet-50 text-violet-700 ring-violet-200",
};

export function TopicRow({ topic }: { topic: StudyTopic }) {
  const revise = useReviseTopic();
  const unmark = useUnmarkTopic();
  const update = useUpdateTopic();
  const remove = useDeleteTopic();

  const [expanded, setExpanded] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState(topic.title);
  const [notesDraft, setNotesDraft] = useState(topic.notes ?? "");
  const [tagDraft, setTagDraft] = useState("");

  const checked = topic.status === "done" || topic.status === "mastered";
  const isMastered = topic.status === "mastered";

  // A topic is stale if it's been marked done/mastered but not revised in 14+ days.
  const STALE_MS = 14 * 24 * 60 * 60 * 1000;
  const isStale =
    checked &&
    (!topic.last_revised_at ||
      Date.now() - new Date(topic.last_revised_at).getTime() > STALE_MS);

  const toggle = () => {
    if (checked) unmark.mutate({ id: topic.id });
    else revise.mutate({ id: topic.id });
  };

  const commitTitle = async () => {
    const trimmed = titleDraft.trim();
    if (!trimmed || trimmed === topic.title) {
      setRenaming(false);
      setTitleDraft(topic.title);
      return;
    }
    try {
      await update.mutateAsync({
        id: topic.id,
        patch: { title: trimmed },
      });
    } finally {
      setRenaming(false);
    }
  };

  const commitNotes = async () => {
    const trimmed = notesDraft.trim();
    if (trimmed === (topic.notes ?? "").trim()) return;
    await update.mutateAsync({
      id: topic.id,
      patch: { notes: trimmed || null },
    });
  };

  const addTag = async () => {
    const t = tagDraft.trim().toLowerCase().replace(/\s+/g, "-");
    if (!t || topic.tags.includes(t)) {
      setTagDraft("");
      return;
    }
    await update.mutateAsync({
      id: topic.id,
      patch: { tags: [...topic.tags, t] },
    });
    setTagDraft("");
  };

  const removeTag = async (t: string) => {
    await update.mutateAsync({
      id: topic.id,
      patch: { tags: topic.tags.filter((x) => x !== t) },
    });
  };

  const setKind = (k: StudyKind) => {
    if (k === topic.kind) return;
    update.mutate({ id: topic.id, patch: { kind: k } });
  };

  return (
    <li className="group/topic">
      <div className="px-2 py-1.5 rounded-lg hover:bg-[var(--color-surface-2)] transition-colors flex items-center gap-2">
        {/* Status checkbox: clickable, animated, shows status dot when unchecked */}
        <button
          type="button"
          onClick={toggle}
          aria-pressed={checked}
          aria-label={
            checked
              ? `Unmark ${topic.title}`
              : `Mark ${topic.title} as revised`
          }
          className={`shrink-0 w-5 h-5 rounded-md grid place-items-center transition-all duration-200 ${
            checked
              ? isMastered
                ? "bg-gradient-to-br from-amber-400 to-fuchsia-500 text-white shadow-md shadow-fuchsia-200"
                : "bg-emerald-500 text-white shadow-sm"
              : "bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] hover:ring-indigo-400"
          }`}
        >
          {checked ? (
            isMastered ? (
              <Sparkles className="w-3 h-3" />
            ) : (
              <Check className="w-3 h-3 stroke-[3]" />
            )
          ) : (
            <span className={`w-1.5 h-1.5 rounded-full ${_STATUS_DOT[topic.status]}`} />
          )}
        </button>

        {/* Title (inline edit on double-click) */}
        {renaming ? (
          <input
            autoFocus
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            onBlur={commitTitle}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitTitle();
              if (e.key === "Escape") {
                setRenaming(false);
                setTitleDraft(topic.title);
              }
            }}
            className="flex-1 bg-[var(--color-surface)] ring-1 ring-indigo-500 rounded px-2 py-0.5 text-[13.5px] text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-500"
          />
        ) : (
          <button
            type="button"
            onDoubleClick={() => setRenaming(true)}
            onClick={() => setExpanded((v) => !v)}
            className={`flex-1 min-w-0 text-left text-[13.5px] truncate ${
              checked ? "text-[var(--color-text-3)] line-through decoration-[var(--color-text-3)]" : "text-[var(--color-text)]"
            }`}
            title="Click to expand · double-click to rename"
          >
            {topic.title}
          </button>
        )}

        {/* Kind badge */}
        <span
          className={`hidden md:inline-flex shrink-0 text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded ring-1 ${
            _KIND_BADGE[topic.kind]
          }`}
        >
          {topic.kind}
        </span>

        {/* Revision count chip (when > 0) */}
        {topic.revision_count > 0 ? (
          <span
            className="shrink-0 text-[10.5px] tabular-nums text-[var(--color-text-3)] px-1.5 py-0.5 rounded-full bg-[var(--color-surface-2)]"
            title={`${topic.revision_count} revision${topic.revision_count === 1 ? "" : "s"}`}
          >
            ×{topic.revision_count}
          </span>
        ) : null}

        {/* Stale indicator — shown when done/mastered but not revised in 14+ days */}
        {isStale ? (
          <span
            className="shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-amber-700 bg-amber-50 ring-1 ring-amber-200 px-1.5 py-0.5 rounded-full"
            title="Due for review — not revised in 14+ days"
          >
            <RefreshCw className="w-2.5 h-2.5" />
            due
          </span>
        ) : null}

        {/* Tag pills (max 2 inline; rest hidden under expander) */}
        {topic.tags.length > 0 ? (
          <div className="hidden lg:flex shrink-0 items-center gap-1 max-w-[180px]">
            {topic.tags.slice(0, 2).map((t) => (
              <span
                key={t}
                className="text-[10.5px] px-1.5 py-0.5 rounded bg-[var(--color-surface-2)] text-[var(--color-text-2)]"
              >
                #{t}
              </span>
            ))}
            {topic.tags.length > 2 ? (
              <span className="text-[10.5px] text-[var(--color-text-3)]">
                +{topic.tags.length - 2}
              </span>
            ) : null}
          </div>
        ) : null}

        {/* Expand toggle */}
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-label={expanded ? "Collapse" : "Expand"}
          className="shrink-0 p-1 rounded text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors opacity-60 group-hover/topic:opacity-100"
        >
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {expanded ? (
        <div className="mx-2 mb-2 mt-1 px-3 py-3 rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] space-y-3 fade-up">
          {/* Kind toggle + tags */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-3)] font-semibold">
              Kind
            </span>
            <KindToggle value={topic.kind} onChange={setKind} />
            <span className="ml-2 inline-flex items-center gap-1 text-[11px] uppercase tracking-wider text-[var(--color-text-3)] font-semibold">
              <Tag className="w-3 h-3" />
              Tags
            </span>
            {topic.tags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] text-[var(--color-text-2)]"
              >
                #{t}
                <button
                  type="button"
                  onClick={() => removeTag(t)}
                  aria-label={`Remove tag ${t}`}
                  className="text-[var(--color-text-3)] hover:text-rose-500"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            ))}
            <input
              value={tagDraft}
              onChange={(e) => setTagDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addTag();
                }
                if (e.key === "Escape") setTagDraft("");
              }}
              onBlur={addTag}
              placeholder="+ tag"
              className="w-24 bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] rounded-full px-2 py-0.5 text-[11px] text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-[var(--color-text-3)]"
            />
          </div>

          {/* Notes (markdown-friendly textarea, saves on blur) */}
          <div>
            <span className="block text-[11px] uppercase tracking-wider text-[var(--color-text-3)] font-semibold mb-1">
              Notes
            </span>
            <textarea
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.target.value)}
              onBlur={commitNotes}
              rows={3}
              placeholder="Anything you want to remember about this topic…"
              className="w-full resize-y bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] rounded-lg px-2.5 py-2 text-[12.5px] text-[var(--color-text)] outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-[var(--color-text-3)]"
            />
          </div>

          {/* Metadata + delete */}
          <div className="flex items-center justify-between text-[11px] text-[var(--color-text-3)] pt-1 border-t border-[var(--color-border)]">
            <div className="flex items-center gap-2">
              <span>
                {topic.revision_count > 0
                  ? `${topic.revision_count} revision${topic.revision_count === 1 ? "" : "s"}`
                  : "Not revised yet"}
              </span>
              {topic.last_revised_at ? (
                <span>· last {_relative(topic.last_revised_at)}</span>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => {
                if (confirm(`Delete topic "${topic.title}"?`)) {
                  remove.mutate(topic.id);
                }
              }}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] text-rose-600 hover:bg-rose-50"
            >
              <Trash2 className="w-3 h-3" />
              Delete
            </button>
          </div>
        </div>
      ) : null}
    </li>
  );
}

function _relative(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.max(0, now - then);
  const m = Math.floor(diff / 60_000);
  if (m < 60) return m <= 1 ? "just now" : `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  const mo = Math.floor(d / 30);
  return `${mo}mo ago`;
}
