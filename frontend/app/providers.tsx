"use client";

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import { ThemeProvider } from "@/lib/theme";

type ToastKind = "success" | "error";
type Toast = { id: number; kind: ToastKind; message: string };

type ToastCtx = { push: (kind: ToastKind, message: string) => void };
const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast() outside <Providers>");
  return ctx;
}

let nextId = 1;

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000, refetchOnWindowFocus: true },
        },
      }),
  );
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback(
    (id: number) => setToasts((t) => t.filter((x) => x.id !== id)),
    [],
  );

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId++;
      setToasts((t) => [...t, { id, kind, message }]);
      if (kind === "success") setTimeout(() => dismiss(id), 4000);
    },
    [dismiss],
  );

  return (
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <ToastContext.Provider value={{ push }}>
          {children}
          <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm">
            {toasts.map((t) => (
              <div
                key={t.id}
                role={t.kind === "error" ? "alert" : "status"}
                onClick={() => dismiss(t.id)}
                className="flex items-start gap-2.5 cursor-pointer bg-[var(--color-surface)] rounded-xl ring-1 ring-[var(--color-border)] shadow-lg pl-4 pr-5 py-3 fade-up"
              >
                {t.kind === "success" ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                )}
                <span className="text-[13.5px] text-[var(--color-text)]">{t.message}</span>
              </div>
            ))}
          </div>
        </ToastContext.Provider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
