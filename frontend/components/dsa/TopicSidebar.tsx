"use client";

import { Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { DsaTopicStats } from "@/lib/types";

export const PRESET_TOPICS = [
  "Arrays",
  "Two Pointers",
  "Sliding Window",
  "Binary Search",
  "Linked Lists",
  "Stacks & Queues",
  "Trees",
  "Graphs",
  "Dynamic Programming",
  "Backtracking",
  "Heaps",
  "Tries",
  "Greedy",
  "Intervals",
  "Math & Bit Manipulation",
];

const STORAGE_KEY = "jp_dsa_custom_topics";

function loadCustomTopics(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function saveCustomTopics(topics: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(topics));
}

interface TopicSidebarProps {
  topics: DsaTopicStats[];
  selected: string | undefined;
  onSelect: (topic: string | undefined) => void;
}

export function TopicSidebar({ topics, selected, onSelect }: TopicSidebarProps) {
  const [customTopics, setCustomTopics] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCustomTopics(loadCustomTopics());
  }, []);

  useEffect(() => {
    if (adding) inputRef.current?.focus();
  }, [adding]);

  const addCustomTopic = () => {
    const name = draft.trim();
    if (!name) { setAdding(false); setDraft(""); return; }
    if ([...PRESET_TOPICS, ...customTopics].some((t) => t.toLowerCase() === name.toLowerCase())) {
      setAdding(false); setDraft(""); return;
    }
    const updated = [...customTopics, name];
    setCustomTopics(updated);
    saveCustomTopics(updated);
    setAdding(false);
    setDraft("");
  };

  const removeCustomTopic = (topic: string) => {
    const updated = customTopics.filter((t) => t !== topic);
    setCustomTopics(updated);
    saveCustomTopics(updated);
    if (selected === topic) onSelect(undefined);
  };

  const topicMap = Object.fromEntries(topics.map((t) => [t.topic, t]));
  const allTopics = Array.from(new Set([...PRESET_TOPICS, ...customTopics, ...topics.map((t) => t.topic)]));

  const btnCls = (active: boolean) =>
    `w-full flex items-center justify-between px-3 py-2 rounded-lg text-[14px] transition-colors ${
      active
        ? "bg-indigo-500/10 text-indigo-400 font-medium"
        : "text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
    }`;

  return (
    <aside className="w-52 shrink-0">
      <div className="flex items-center justify-between px-2 mb-3">
        <h2 className="text-[11px] uppercase tracking-widest text-[var(--color-text-3)]">Topics</h2>
        <button
          type="button"
          onClick={() => setAdding(true)}
          title="Add custom topic"
          className="p-0.5 rounded text-[var(--color-text-3)] hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <nav className="flex flex-col gap-0.5">
        <button
          type="button"
          onClick={() => onSelect(undefined)}
          className={btnCls(!selected)}
        >
          <span>All</span>
          <span className="text-[12px] tabular-nums text-[var(--color-text-3)]">
            {topics.reduce((s, t) => s + t.count, 0)}
          </span>
        </button>

        {allTopics.map((topic) => {
          const stat = topicMap[topic];
          const isCustom = customTopics.includes(topic);
          return (
            <div key={topic} className="group relative flex items-center">
              <button
                type="button"
                onClick={() => onSelect(topic)}
                className={`${btnCls(selected === topic)} pr-7`}
              >
                <span className="truncate">{topic}</span>
                {stat ? (
                  <span className="text-[12px] tabular-nums text-[var(--color-text-3)]">
                    {stat.count}
                  </span>
                ) : null}
              </button>
              {isCustom ? (
                <button
                  type="button"
                  onClick={() => removeCustomTopic(topic)}
                  className="absolute right-1.5 opacity-0 group-hover:opacity-100 p-0.5 rounded text-[var(--color-text-3)] hover:text-rose-500 transition-all"
                  title="Remove topic"
                >
                  <X className="w-3 h-3" />
                </button>
              ) : null}
            </div>
          );
        })}

        {adding ? (
          <div className="flex items-center gap-1 px-2 py-1">
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addCustomTopic();
                if (e.key === "Escape") { setAdding(false); setDraft(""); }
              }}
              onBlur={addCustomTopic}
              placeholder="Topic name…"
              className="flex-1 min-w-0 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2 py-1 text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-1 focus:ring-indigo-500/60"
            />
          </div>
        ) : null}
      </nav>
    </aside>
  );
}
