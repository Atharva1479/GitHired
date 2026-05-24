"use client";

import { FileText, Upload, X } from "lucide-react";
import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import {
  useCreateApplication,
  useUploadApplicationFile,
} from "@/hooks/useApplications";
import { SOURCES, type FileKind, type Source } from "@/lib/types";

export function AddApplication({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const create = useCreateApplication();
  const upload = useUploadApplicationFile();
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);

  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [source, setSource] = useState<Source>("LinkedIn");
  const [appliedDate, setAppliedDate] = useState(today);
  const [jdUrl, setJdUrl] = useState("");
  const [jdText, setJdText] = useState("");
  const [referredBy, setReferredBy] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [coverLetterFile, setCoverLetterFile] = useState<File | null>(null);

  function reset() {
    setCompany("");
    setRole("");
    setSource("LinkedIn");
    setAppliedDate(today);
    setJdUrl("");
    setJdText("");
    setReferredBy("");
    setResumeFile(null);
    setCoverLetterFile(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      const created = await create.mutateAsync({
        company,
        role,
        source,
        applied_date: appliedDate,
        jd_url: jdUrl || null,
        jd_text: jdText || null,
        contact_name: referredBy || null,
      });

      const tasks: Array<{ kind: FileKind; file: File }> = [];
      if (resumeFile) tasks.push({ kind: "resume", file: resumeFile });
      if (coverLetterFile)
        tasks.push({ kind: "cover_letter", file: coverLetterFile });

      const results = await Promise.allSettled(
        tasks.map((t) =>
          upload.mutateAsync({ id: created.id, kind: t.kind, file: t.file }),
        ),
      );
      const failed = results.filter((r) => r.status === "rejected").length;

      toast.push("success", `${company} added`);
      if (failed > 0) {
        toast.push(
          "error",
          `${failed} attachment${failed > 1 ? "s" : ""} failed — retry from the card`,
        );
      }
      reset();
      onClose();
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Failed to add",
      );
    }
  }

  const busy = create.isPending || upload.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New application"
      subtitle="Log a role you've applied to. You can edit any field later."
    >
      <form onSubmit={submit} className="flex flex-col">
        <p className="text-[12px] text-[var(--color-text-3)] mb-3">
          Fields marked <span className="text-red-500">*</span> are required.
        </p>
        <div className="space-y-4">
          <Input
            id="f-company"
            label="Company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
            autoFocus
            placeholder="Stripe"
          />
          <Input
            id="f-role"
            label="Role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            required
            placeholder="Software Engineer"
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              id="f-source"
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
              id="f-date"
              label="Date applied"
              type="date"
              value={appliedDate}
              onChange={(e) => setAppliedDate(e.target.value)}
              required
            />
          </div>
          <Input
            id="f-url"
            label="Job posting URL"
            type="url"
            value={jdUrl}
            onChange={(e) => setJdUrl(e.target.value)}
            placeholder="https://company.com/careers/123"
          />
          <Input
            id="f-referred-by"
            label="Referred by"
            hint="Name of the person who referred you, if any."
            value={referredBy}
            onChange={(e) => setReferredBy(e.target.value)}
            placeholder="Full name"
          />

          <div className="space-y-1.5">
            <label
              htmlFor="f-jd"
              className="block text-[13px] font-medium text-[var(--color-text)]"
            >
              Job description
            </label>
            <textarea
              id="f-jd"
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={5}
              placeholder="Paste the job description"
              className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[14px] text-[var(--color-text)] ring-1 ring-inset ring-[var(--color-border)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm transition-shadow resize-y"
            />
            <p className="text-[12px] text-[var(--color-text-3)]">
              Used to personalize follow-up drafts. You can paste the full
              posting or just the responsibilities section.
            </p>
          </div>

          <FilePicker
            label="Resume"
            file={resumeFile}
            onChange={setResumeFile}
          />
          <FilePicker
            label="Cover letter"
            file={coverLetterFile}
            onChange={setCoverLetterFile}
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-4 mt-4 border-t border-[var(--color-border)]">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save application"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function FilePicker({
  label,
  file,
  onChange,
}: {
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);

  function pick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    e.target.value = "";
    if (f && f.type !== "application/pdf") {
      // toast not available here — keep silent + reject
      return;
    }
    onChange(f);
  }

  return (
    <div className="space-y-1.5">
      <label className="block text-[13px] font-medium text-[var(--color-text)]">
        {label}
      </label>
      <div className="flex items-center gap-2 rounded-lg ring-1 ring-inset ring-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 shadow-sm">
        <button
          type="button"
          onClick={() => ref.current?.click()}
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] transition-colors"
        >
          <Upload className="w-3.5 h-3.5" />
          {file ? "Replace" : "Upload PDF"}
        </button>
        <span className="flex-1 min-w-0 flex items-center gap-1.5 text-[12.5px] text-[var(--color-text-3)] truncate">
          {file ? (
            <>
              <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="truncate text-[var(--color-text-2)]">{file.name}</span>
            </>
          ) : (
            <span>PDF, max 10 MB</span>
          )}
        </span>
        {file ? (
          <button
            type="button"
            onClick={() => onChange(null)}
            aria-label="Remove file"
            className="rounded-md p-1 text-[var(--color-text-3)] hover:text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
        <input
          ref={ref}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={pick}
        />
      </div>
    </div>
  );
}
