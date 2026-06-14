"use client";

import { Download, Loader2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

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
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const prevSrc = useRef<string | null>(null);

  // Fetch PDF as blob with credentials so the auth cookie is included.
  // This bypasses cross-origin iframe cookie restrictions.
  useEffect(() => {
    if (!open) return;
    if (prevSrc.current === src && blobUrl) return;
    prevSrc.current = src;
    setBlobUrl(null);
    setError(false);

    let revoke: string | null = null;
    fetch(src, { credentials: "include" })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        revoke = URL.createObjectURL(blob);
        setBlobUrl(revoke);
      })
      .catch(() => setError(true));

    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [open, src]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
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

        {error ? (
          <div className="flex-1 flex items-center justify-center text-[var(--color-text-3)] text-sm">
            Could not load file. Try the Download button above.
          </div>
        ) : blobUrl ? (
          <iframe
            src={blobUrl}
            title={title}
            className="flex-1 w-full bg-[var(--color-surface-2)]"
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-[var(--color-text-3)]">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
