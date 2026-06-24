import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { useJobSearch } from "@/hooks/useJobs";
import type { JobResult } from "@/types/jobs";

vi.mock("@/lib/jobs-api", () => ({
  searchJobs: vi.fn(),
}));

import { searchJobs } from "@/lib/jobs-api";

function makeJob(overrides: Partial<JobResult> = {}): JobResult {
  return {
    id: 1,
    source: "jsearch",
    external_id: "ext-1",
    title: "Software Engineer",
    company: "Acme",
    location: "Remote",
    description: "Description",
    apply_url: "https://example.com/apply",
    posted_at: null,
    employment_type: "FULLTIME",
    skills: [],
    hours_old: 10,
    freshness_score: 0.8,
    freshness_label: "⚡ 6–24h",
    freshness_color: "green",
    est_applicants: "<10",
    velocity_label: null,
    bookmark_status: null,
    is_remote: false,
    salary_min: null,
    salary_max: null,
    salary_currency: null,
    tags: [],
    semantic_score: null,
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useJobSearch freshness filter", () => {
  beforeEach(() => {
    vi.mocked(searchJobs).mockResolvedValue([
      makeJob({ id: 1, hours_old: 5 }),   // fresh: <6h
      makeJob({ id: 2, hours_old: 20 }),  // acceptable: <24h
      makeJob({ id: 3, hours_old: 48 }),  // stale at <24h cutoff
      makeJob({ id: 4, hours_old: null }), // unknown — always pass through
    ]);
  });

  it("returns all jobs when freshnessHours=72 (default)", async () => {
    const { result } = renderHook(
      () => useJobSearch({ q: "engineer" }, 72),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.filteredData).toHaveLength(4);
  });

  it("filters jobs older than freshnessHours", async () => {
    const { result } = renderHook(
      () => useJobSearch({ q: "engineer" }, 24),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // id:1 (5h), id:2 (20h), id:4 (null) pass — id:3 (48h) is excluded
    expect(result.current.filteredData.map((j) => j.id)).toEqual([1, 2, 4]);
  });

  it("passes through jobs with hours_old=null regardless of freshnessHours", async () => {
    const { result } = renderHook(
      () => useJobSearch({ q: "engineer" }, 1),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Only id:4 (null) should pass the strict 1h window
    const ids = result.current.filteredData.map((j) => j.id);
    expect(ids).toContain(4);
    expect(ids).not.toContain(3);
  });

  it("is disabled when params is null", () => {
    const { result } = renderHook(
      () => useJobSearch(null),
      { wrapper },
    );
    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe("idle");
    expect(searchJobs).not.toHaveBeenCalled();
  });

  it("is disabled when query string is empty", () => {
    const { result } = renderHook(
      () => useJobSearch({ q: "  " }),
      { wrapper },
    );
    expect(result.current.fetchStatus).toBe("idle");
    expect(searchJobs).not.toHaveBeenCalled();
  });

  it("filteredData is empty array while loading", () => {
    vi.mocked(searchJobs).mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(
      () => useJobSearch({ q: "engineer" }),
      { wrapper },
    );
    expect(result.current.filteredData).toEqual([]);
  });

  it("changing freshnessHours does not trigger a new API call", async () => {
    const { result, rerender } = renderHook(
      ({ hours }: { hours: number }) => useJobSearch({ q: "engineer" }, hours),
      { wrapper, initialProps: { hours: 72 } },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(searchJobs).toHaveBeenCalledTimes(1);

    rerender({ hours: 24 });
    // filteredData changes but no new API call
    expect(searchJobs).toHaveBeenCalledTimes(1);
    expect(result.current.filteredData.map((j) => j.id)).toEqual([1, 2, 4]);
  });
});
