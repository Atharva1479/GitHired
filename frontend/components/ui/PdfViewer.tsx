"use client";

import { Download, X } from "lucide-react";
import { useEffect } from "react";

export function PdfViewer({
  open,
  src,
  downloadHref,
  title,
  onClose,
}: {
  open: boolean;
  src: string;
  downloadHref: string;
  title: string;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 fade-up"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl h-[90vh] flex flex-col rounded-2xl bg-[var(--color-surface)] shadow-2xl ring-1 ring-[var(--color-border)] overflow-hidden"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border)]">
          <div className="min-w-0">
            <div className="text-[14.5px] font-semibold text-[var(--color-text)] truncate">
              {title}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <a
              href={downloadHref}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[13px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
            >
              <Download className="w-4 h-4" />
              Download
            </a>
            <button
              onClick={onClose}
              aria-label="Close"
              className="rounded-md p-1.5 text-[var(--color-text-3)] hover:text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <iframe
          src={src}
          title={title}
          className="flex-1 w-full bg-[var(--color-surface-2)]"
        />
      </div>
    </div>
  );
}
