import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { useHistory, useStartSession, useEndSession } from "@/hooks/useInterview";

vi.mock("@/lib/interview-api", () => ({
  startSession: vi.fn(),
  endSession: vi.fn(),
  getHistory: vi.fn().mockResolvedValue([]),
  getReport: vi.fn(),
  submitTurn: vi.fn(),
  deleteSession: vi.fn(),
  startAgentSession: vi.fn(),
  submitAnswer: vi.fn(),
}));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useHistory", () => {
  it("fetches history on mount", async () => {
    const { result } = renderHook(() => useHistory(), { wrapper });
    expect(result.current.isLoading).toBe(true);
  });
});

describe("useStartSession", () => {
  it("exposes a mutateAsync function", () => {
    const { result } = renderHook(() => useStartSession(), { wrapper });
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("useEndSession", () => {
  it("exposes a mutateAsync function", () => {
    const { result } = renderHook(() => useEndSession(), { wrapper });
    expect(typeof result.current.mutateAsync).toBe("function");
  });
});

describe("INTERVIEW_KEYS", () => {
  it("report key includes session id", async () => {
    // Import and verify key structure for stable cache invalidation
    const { INTERVIEW_KEYS } = await import("@/hooks/useInterview");
    expect(INTERVIEW_KEYS.report(42)).toEqual(["interview", "report", 42]);
    expect(INTERVIEW_KEYS.history()).toEqual(["interview", "history"]);
  });

  it("report key changes with different session ids", async () => {
    const { INTERVIEW_KEYS } = await import("@/hooks/useInterview");
    const key1 = JSON.stringify(INTERVIEW_KEYS.report(1));
    const key2 = JSON.stringify(INTERVIEW_KEYS.report(2));
    expect(key1).not.toBe(key2);
  });
});
