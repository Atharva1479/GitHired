"use client";
import { useRef, useState } from "react";
import { X, Upload } from "lucide-react";
import { useUploadResume } from "@/hooks/useResumes";

const ROLE_SUGGESTIONS = [
  "Java Developer",
  "Python Developer",
  "Agentic AI Developer",
  "Full Stack Developer",
  "Frontend Developer",
  "Backend Developer",
  "DevOps Engineer",
  "Data Engineer",
];

interface Props {
  onClose: () => void;
}

export function UploadResumeModal({ onClose }: Props) {
  const { mutateAsync, isPending } = useUploadResume();
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [roleTag, setRoleTag] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!name.trim() || !roleTag.trim() || !file) {
      setError("All fields are required.");
      return;
    }
    try {
      await mutateAsync({ name: name.trim(), roleTag: roleTag.trim(), file });
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[15px] font-semibold">Upload Resume</h2>
          <button onClick={onClose} className="text-[var(--color-text-3)] hover:text-[var(--color-text)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-[var(--color-text-3)] mb-1">
              Display Name
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Atharva_Java_2026"
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[var(--color-text-3)] mb-1">
              Target Role
            </label>
            <input
              value={roleTag}
              onChange={(e) => setRoleTag(e.target.value)}
              list="role-suggestions"
              placeholder="e.g. Java Developer"
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <datalist id="role-suggestions">
              {ROLE_SUGGESTIONS.map((r) => <option key={r} value={r} />)}
            </datalist>
            <p className="text-[11px] text-[var(--color-text-3)] mt-1">
              Used to match this resume against your applications for that role.
            </p>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[var(--color-text-3)] mb-1">
              Resume File (PDF)
            </label>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-3 text-sm text-[var(--color-text-3)] hover:border-indigo-400 transition-colors"
            >
              <Upload className="w-4 h-4" />
              {file ? file.name : "Choose PDF file"}
            </button>
          </div>

          {error && <p className="text-[12px] text-red-500">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={isPending}
            className="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {isPending ? "Uploading…" : "Upload Resume"}
          </button>
        </div>
      </div>
    </div>
  );
}
