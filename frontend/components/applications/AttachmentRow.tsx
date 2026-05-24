"use client";

import { Download, Eye, FileText, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { useToast } from "@/app/providers";
import { PdfViewer } from "@/components/ui/PdfViewer";
import {
  useDeleteApplicationFile,
  useUploadApplicationFile,
} from "@/hooks/useApplications";
import { fileUrl } from "@/lib/api";
import { FILE_KIND_LABEL, type FileKind } from "@/lib/types";

export function AttachmentRow({
  appId,
  kind,
  fileName,
}: {
  appId: number;
  kind: FileKind;
  fileName: string | null;
}) {
  const upload = useUploadApplicationFile();
  const del = useDeleteApplicationFile();
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [viewing, setViewing] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.type !== "application/pdf") {
      toast.push("error", "Only PDF files are supported");
      return;
    }
    try {
      await upload.mutateAsync({ id: appId, kind, file: f });
      toast.push("success", `${FILE_KIND_LABEL[kind]} uploaded`);
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Upload failed",
      );
    }
  }

  async function handleDelete() {
    if (!confirm(`Remove the ${FILE_KIND_LABEL[kind].toLowerCase()}?`)) return;
    try {
      await del.mutateAsync({ id: appId, kind });
      toast.push("success", `${FILE_KIND_LABEL[kind]} removed`);
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Couldn't remove",
      );
    }
  }

  const present = !!fileName;
  const viewSrc = fileUrl(appId, kind, false);
  const downloadSrc = fileUrl(appId, kind, true);

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <span
          className={`w-9 h-9 rounded-lg grid place-items-center shrink-0 ${
            present
              ? "bg-indigo-500/10 text-indigo-400"
              : "bg-[var(--color-surface-2)] text-[var(--color-text-3)]"
          }`}
        >
          <FileText className="w-[18px] h-[18px]" />
        </span>
        <div className="min-w-0">
          <div className="text-[13.5px] font-medium text-[var(--color-text)]">
            {FILE_KIND_LABEL[kind]}
          </div>
          <div className="text-[12px] text-[var(--color-text-3)] truncate">
            {present ? fileName : "No file uploaded yet · PDF up to 10 MB"}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFile}
        />
        {present ? (
          <>
            <button
              onClick={() => setViewing(true)}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
              title="View"
            >
              <Eye className="w-3.5 h-3.5" />
              View
            </button>
            <a
              href={downloadSrc}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
              title="Download"
            >
              <Download className="w-3.5 h-3.5" />
            </a>
            <button
              onClick={() => fileInput.current?.click()}
              disabled={upload.isPending}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors disabled:opacity-50"
              title="Replace"
            >
              <Upload className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleDelete}
              disabled={del.isPending}
              className="inline-flex items-center justify-center rounded-md w-8 h-8 text-[var(--color-text-3)] hover:text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50"
              title="Remove"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </>
        ) : (
          <button
            onClick={() => fileInput.current?.click()}
            disabled={upload.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-3 h-8 text-[12.5px] font-medium shadow-sm transition-colors disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" />
            {upload.isPending ? "Uploading…" : "Upload"}
          </button>
        )}
      </div>

      <PdfViewer
        open={viewing}
        src={viewSrc}
        downloadHref={downloadSrc}
        title={`${FILE_KIND_LABEL[kind]} · ${fileName ?? ""}`}
        onClose={() => setViewing(false)}
      />
    </div>
  );
}
