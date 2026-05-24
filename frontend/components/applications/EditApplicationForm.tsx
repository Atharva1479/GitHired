"use client";

import { useState, type FormEvent } from "react";

import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useUpdateApplication } from "@/hooks/useApplications";
import {
  SOURCES,
  STATUSES,
  type Application,
  type ApplicationUpdate,
  type Source,
  type Status,
} from "@/lib/types";

function diff(
  before: Application,
  next: ApplicationUpdate,
): ApplicationUpdate {
  const out: ApplicationUpdate = {};
  for (const key of Object.keys(next) as (keyof ApplicationUpdate)[]) {
    const a = (before as unknown as Record<string, unknown>)[key];
    const b = (next as unknown as Record<string, unknown>)[key];
    const normA = a ?? null;
    const normB = b ?? null;
    if (normA !== normB) {
      (out as Record<string, unknown>)[key] = b;
    }
  }
  return out;
}

export function EditApplicationForm({
  app,
  onDone,
  onCancel,
}: {
  app: Application;
  onDone: () => void;
  onCancel: () => void;
}) {
  const update = useUpdateApplication();
  const toast = useToast();

  const [company, setCompany] = useState(app.company);
  const [role, setRole] = useState(app.role);
  const [source, setSource] = useState<Source>(app.source);
  const [status, setStatus] = useState<Status>(app.status);
  const [appliedDate, setAppliedDate] = useState(app.applied_date);
  const [jdUrl, setJdUrl] = useState(app.jd_url ?? "");
  const [jdText, setJdText] = useState(app.jd_text ?? "");
  const [contactName, setContactName] = useState(app.contact_name ?? "");
  const [salaryDiscussed, setSalaryDiscussed] = useState(
    app.salary_discussed ?? "",
  );
  const [fitScore, setFitScore] = useState(
    app.fit_score == null ? "" : String(app.fit_score),
  );
  const [notes, setNotes] = useState(app.notes ?? "");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: ApplicationUpdate = {
      company: company.trim(),
      role: role.trim(),
      source,
      status,
      applied_date: appliedDate,
      jd_url: jdUrl.trim() || null,
      jd_text: jdText.trim() || null,
      contact_name: contactName.trim() || null,
      salary_discussed: salaryDiscussed.trim() || null,
      fit_score: fitScore === "" ? null : Number(fitScore),
      notes: notes.trim() || null,
    };
    const patch = diff(app, next);
    if (Object.keys(patch).length === 0) {
      onDone();
      return;
    }
    try {
      await update.mutateAsync({ id: app.id, patch });
      toast.push("success", "Application updated");
      onDone();
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Couldn't update",
      );
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <p className="text-[12px] text-[var(--color-text-3)]">
        Fields marked <span className="text-red-500">*</span> are required.
      </p>
      <Input
        id="e-company"
        label="Company"
        value={company}
        onChange={(e) => setCompany(e.target.value)}
        required
      />
      <Input
        id="e-role"
        label="Role"
        value={role}
        onChange={(e) => setRole(e.target.value)}
        required
      />
      <div className="grid grid-cols-2 gap-3">
        <Select
          id="e-source"
          label="Source"
          value={source}
          onChange={(e) => setSource(e.target.value as Source)}
          required
        >
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <Input
          id="e-date"
          label="Date applied"
          type="date"
          value={appliedDate}
          onChange={(e) => setAppliedDate(e.target.value)}
          required
        />
      </div>
      <Select
        id="e-status"
        label="Status"
        value={status}
        onChange={(e) => setStatus(e.target.value as Status)}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </Select>
      <Input
        id="e-url"
        label="Job posting URL"
        type="url"
        value={jdUrl}
        onChange={(e) => setJdUrl(e.target.value)}
        placeholder="https://company.com/careers/123"
      />
      <Input
        id="e-referred"
        label="Referred by"
        value={contactName}
        onChange={(e) => setContactName(e.target.value)}
        placeholder="Full name"
      />
      <div className="grid grid-cols-2 gap-3">
        <Input
          id="e-fit"
          label="Fit score (0–100)"
          type="number"
          min={0}
          max={100}
          value={fitScore}
          onChange={(e) => setFitScore(e.target.value)}
        />
        <Input
          id="e-salary"
          label="Salary discussed"
          value={salaryDiscussed}
          onChange={(e) => setSalaryDiscussed(e.target.value)}
          placeholder="e.g. ₹18 LPA"
        />
      </div>
      <div className="space-y-1.5">
        <label
          htmlFor="e-jd"
          className="block text-[13px] font-medium text-[var(--color-text)]"
        >
          Job description
        </label>
        <textarea
          id="e-jd"
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={5}
          placeholder="Paste the job description"
          className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
        />
      </div>
      <div className="space-y-1.5">
        <label
          htmlFor="e-notes"
          className="block text-[13px] font-medium text-[var(--color-text)]"
        >
          Notes
        </label>
        <textarea
          id="e-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Private notes — not sent to the company."
          className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
        />
      </div>

      <div className="flex items-center justify-end gap-2 pt-4 border-t border-[var(--color-border)]">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
