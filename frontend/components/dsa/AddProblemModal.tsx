"use client";

import { useState } from "react";

import { useCreateDsaProblem } from "@/hooks/useDsa";
import type { DsaDifficulty, DsaProblemCreate, DsaProblemOut } from "@/lib/types";

import { PRESET_TOPICS } from "./TopicSidebar";

interface AddProblemModalProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (problem: DsaProblemOut) => void;
}

const EMPTY: DsaProblemCreate = {
  title: "",
  topic: "",
  difficulty: "medium",
  source_url: "",
  description: "",
  user_solution: "",
};

const inputCls =
  "w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-[14px] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 transition-shadow";

export function AddProblemModal({ open, onClose, onCreated }: AddProblemModalProps) {
  const [form, setForm] = useState<DsaProblemCreate>(EMPTY);
  const create = useCreateDsaProblem();

  if (!open) return null;

  const set = (key: keyof DsaProblemCreate, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const hasSolution = !!form.user_solution;
    const problem = await create.mutateAsync({
      ...form,
      source_url: form.source_url || undefined,
      description: form.description || undefined,
      user_solution: form.user_solution || undefined,
    });
    setForm(EMPTY);
    onClose();
    if (hasSolution && onCreated) {
      onCreated(problem);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-[var(--color-surface)] rounded-2xl ring-1 ring-[var(--color-border)] w-full max-w-2xl mx-4 shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-[16px] font-semibold text-[var(--color-text)]">Log a Problem</h2>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4 max-h-[80vh] overflow-y-auto">
          <div>
            <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
              Problem Title <span className="text-rose-500">*</span>
            </label>
            <input
              required
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="e.g. Two Sum"
              className={inputCls}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
                Topic <span className="text-rose-500">*</span>
              </label>
              <input
                required
                list="dsa-topics"
                value={form.topic}
                onChange={(e) => set("topic", e.target.value)}
                placeholder="Arrays, Graphs…"
                className={inputCls}
              />
              <datalist id="dsa-topics">
                {PRESET_TOPICS.map((t) => <option key={t} value={t} />)}
              </datalist>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
                Difficulty
              </label>
              <select
                value={form.difficulty}
                onChange={(e) => set("difficulty", e.target.value as DsaDifficulty)}
                className={inputCls}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
              Problem Link
            </label>
            <input
              type="url"
              value={form.source_url}
              onChange={(e) => set("source_url", e.target.value)}
              placeholder="https://leetcode.com/problems/two-sum"
              className={inputCls}
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
              Problem Description
            </label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="Paste the problem statement…"
              className={`${inputCls} resize-none`}
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[var(--color-text)] mb-1.5">
              Your Solution
            </label>
            <textarea
              rows={8}
              value={form.user_solution}
              onChange={(e) => set("user_solution", e.target.value)}
              placeholder="Paste your solution code here. AI will analyze it when you click Analyze."
              className={`${inputCls} font-mono resize-y`}
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-[14px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="px-5 py-2 rounded-lg text-[14px] font-medium bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:opacity-60"
            >
              {create.isPending ? "Saving…" : "Save Problem"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
