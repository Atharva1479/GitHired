import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { type ReactNode, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useCreateApplication,
  useDeleteApplication,
  useUpdateApplication,
} from "@/hooks/useApplications";
import type { Application } from "@/lib/types";

// ── Mock API ──────────────────────────────────────────────────────────────────

const mockApiCreate = vi.fn();
const mockApiUpdate = vi.fn();
const mockApiRemove = vi.fn();
const mockApiList   = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    applications: {
      list:   (...args: unknown[]) => mockApiList(...args),
      create: (...args: unknown[]) => mockApiCreate(...args),
      update: (...args: unknown[]) => mockApiUpdate(...args),
      remove: (...args: unknown[]) => mockApiRemove(...args),
    },
  },
}));

// ── Shared fixtures ───────────────────────────────────────────────────────────

const mockApp: Application = {
  id: 1,
  company: "Stripe",
  role: "SWE",
  status: "Applied",
  source: "LinkedIn",
  applied_date: "2026-01-01",
  jd_url: null,
  jd_text: null,
  contact_name: null,
  resume_key: null,
  cover_letter_key: null,
  notes: null,
  fit_score: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  soft_deleted: false,
};

// ── Wrapper helpers ───────────────────────────────────────────────────────────

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function freshQC() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ── useCreateApplication ──────────────────────────────────────────────────────

describe("useCreateApplication", () => {
  it("calls api.applications.create with the supplied payload", async () => {
    const qc = freshQC();
    mockApiCreate.mockResolvedValue({ ...mockApp, id: 99 });

    const { result } = renderHook(() => useCreateApplication(), {
      wrapper: makeWrapper(qc),
    });

    const payload = {
      company: "Stripe",
      role: "SWE",
      source: "LinkedIn" as const,
      applied_date: "2026-01-01",
    };
    await result.current.mutateAsync(payload);

    expect(mockApiCreate).toHaveBeenCalledWith(payload);
  });

  it("invalidates the applications list cache after success", async () => {
    const qc = freshQC();
    mockApiCreate.mockResolvedValue({ ...mockApp, id: 99 });
    mockApiList.mockResolvedValue([]);

    // Seed the cache with a query so invalidation is observable
    qc.setQueryData(["applications", "all"], [mockApp]);

    const { result } = renderHook(() => useCreateApplication(), {
      wrapper: makeWrapper(qc),
    });

    await result.current.mutateAsync({
      company: "Stripe",
      role: "SWE",
      source: "LinkedIn" as const,
      applied_date: "2026-01-01",
    });

    // invalidateQueries marks the cache as stale; observers will re-fetch
    const state = qc.getQueryState(["applications", "all"]);
    expect(state?.isInvalidated).toBe(true);
  });
});

// ── useUpdateApplication ──────────────────────────────────────────────────────

describe("useUpdateApplication", () => {
  it("applies the patch optimistically before the server responds", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);

    let resolveUpdate!: (v: Application) => void;
    mockApiUpdate.mockReturnValueOnce(
      new Promise<Application>((r) => {
        resolveUpdate = r;
      }),
    );

    const { result } = renderHook(() => useUpdateApplication(), {
      wrapper: makeWrapper(qc),
    });

    // Start the mutation, do NOT await
    const mutationPromise = result.current.mutateAsync({
      id: 1,
      patch: { status: "Screening" },
    });

    // Wait for onMutate microtasks (cancelQueries + optimistic set)
    await new Promise((r) => setTimeout(r, 0));

    const optimistic = qc.getQueryData<Application[]>(["applications", "all"]);
    expect(optimistic?.[0].status).toBe("Screening");

    // Clean up: resolve so the promise doesn't hang
    resolveUpdate({ ...mockApp, status: "Screening" });
    await mutationPromise;
  });

  it("rolls back the cache when the server returns an error", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);
    mockApiUpdate.mockRejectedValueOnce(new Error("Server error"));

    const { result } = renderHook(() => useUpdateApplication(), {
      wrapper: makeWrapper(qc),
    });

    await result.current.mutateAsync({ id: 1, patch: { status: "Screening" } }).catch(() => {
      // expected
    });

    // Wait for onError + onSettled
    await waitFor(() => {
      const data = qc.getQueryData<Application[]>(["applications", "all"]);
      expect(data?.[0].status).toBe("Applied");
    });
  });

  it("sends the correct patch fields to the API", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);
    mockApiUpdate.mockResolvedValue({ ...mockApp, status: "Interview" });

    const { result } = renderHook(() => useUpdateApplication(), {
      wrapper: makeWrapper(qc),
    });

    await result.current.mutateAsync({ id: 1, patch: { status: "Interview" } });

    expect(mockApiUpdate).toHaveBeenCalledWith(1, { status: "Interview" });
  });
});

// ── useDeleteApplication ──────────────────────────────────────────────────────

describe("useDeleteApplication", () => {
  it("removes the item from cache optimistically before server responds", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);

    let resolveRemove!: (v: null) => void;
    mockApiRemove.mockReturnValueOnce(
      new Promise<null>((r) => {
        resolveRemove = r;
      }),
    );

    const { result } = renderHook(() => useDeleteApplication(), {
      wrapper: makeWrapper(qc),
    });

    const mutationPromise = result.current.mutateAsync(1);
    await new Promise((r) => setTimeout(r, 0));

    const optimistic = qc.getQueryData<Application[]>(["applications", "all"]);
    expect(optimistic).toHaveLength(0);

    resolveRemove(null);
    await mutationPromise;
  });

  it("rolls back the cache when delete fails", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);
    mockApiRemove.mockRejectedValueOnce(new Error("Delete failed"));

    const { result } = renderHook(() => useDeleteApplication(), {
      wrapper: makeWrapper(qc),
    });

    await result.current.mutateAsync(1).catch(() => {});

    await waitFor(() => {
      const data = qc.getQueryData<Application[]>(["applications", "all"]);
      expect(data).toHaveLength(1);
      expect(data?.[0].id).toBe(1);
    });
  });

  it("calls api.applications.remove with the correct id", async () => {
    const qc = freshQC();
    qc.setQueryData(["applications", "all"], [mockApp]);
    mockApiRemove.mockResolvedValue(null);

    const { result } = renderHook(() => useDeleteApplication(), {
      wrapper: makeWrapper(qc),
    });

    await result.current.mutateAsync(1);
    expect(mockApiRemove).toHaveBeenCalledWith(1);
  });
});
