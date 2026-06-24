import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import JobCard from "@/components/jobs/JobCard";
import type { JobResult } from "@/types/jobs";

function makeJob(overrides: Partial<JobResult> = {}): JobResult {
  return {
    id: 42,
    source: "jsearch",
    external_id: "ext-42",
    title: "Frontend Engineer",
    company: "Stripe",
    location: "Remote",
    description: "Build great UIs",
    apply_url: "https://stripe.com/jobs/42",
    posted_at: null,
    employment_type: "FULLTIME",
    skills: ["React", "TypeScript", "CSS"],
    hours_old: 5,
    freshness_score: 80,
    freshness_label: "🔥 <6h",
    freshness_color: "emerald",
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

describe("JobCard rendering", () => {
  it("shows job title", () => {
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("Frontend Engineer")).toBeInTheDocument();
  });

  it("shows company name", () => {
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("Stripe")).toBeInTheDocument();
  });

  it("shows freshness label", () => {
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("🔥 <6h")).toBeInTheDocument();
  });

  it("shows location", () => {
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("Remote")).toBeInTheDocument();
  });

  it("renders up to 6 skills", () => {
    const job = makeJob({
      skills: ["React", "TypeScript", "CSS", "GraphQL", "Node.js", "Rust", "Go"],
    });
    render(
      <JobCard job={job} onApply={vi.fn()} onBookmark={vi.fn()} onPreview={vi.fn()} />,
    );
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
    // 7th skill hidden → "+1 more" shown
    expect(screen.queryByText("Go")).not.toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("shows Apply & Track button when not yet applied", () => {
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /apply & track/i })).toBeInTheDocument();
  });

  it("shows View Posting link when already applied", () => {
    render(
      <JobCard
        job={makeJob({ bookmark_status: "applied" })}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByRole("link", { name: /view posting/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply & track/i })).not.toBeInTheDocument();
  });

  it("shows ✓ Applied chip when already applied", () => {
    render(
      <JobCard
        job={makeJob({ bookmark_status: "applied" })}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("✓ Applied")).toBeInTheDocument();
  });

  it("shows salary range when both min and max present (USD)", () => {
    render(
      <JobCard
        job={makeJob({ salary_min: 120000, salary_max: 160000, salary_currency: "USD" })}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={vi.fn()}
      />,
    );
    expect(screen.getByText("$120k–$160k")).toBeInTheDocument();
  });
});

describe("JobCard interactions", () => {
  it("clicking the card calls onPreview with the job", async () => {
    const onPreview = vi.fn();
    const job = makeJob();
    render(
      <JobCard job={job} onApply={vi.fn()} onBookmark={vi.fn()} onPreview={onPreview} />,
    );
    // Click the card div (not a button)
    const card = screen.getByText("Frontend Engineer").closest("div[class*=rounded]")!;
    await userEvent.click(card);
    expect(onPreview).toHaveBeenCalledWith(job);
  });

  it("clicking Apply & Track calls onApply with the job", async () => {
    const onApply = vi.fn();
    const job = makeJob();
    render(
      <JobCard job={job} onApply={onApply} onBookmark={vi.fn()} onPreview={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    expect(onApply).toHaveBeenCalledWith(job);
  });

  it("clicking Apply & Track does NOT also call onPreview", async () => {
    const onPreview = vi.fn();
    const onApply = vi.fn();
    const job = makeJob();
    render(
      <JobCard job={job} onApply={onApply} onBookmark={vi.fn()} onPreview={onPreview} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /apply & track/i }));
    expect(onPreview).not.toHaveBeenCalled();
  });

  it("clicking bookmark calls onBookmark and toggles icon", async () => {
    const onBookmark = vi.fn();
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={onBookmark}
        onPreview={vi.fn()}
      />,
    );
    const btn = screen.getByTitle("Bookmark");
    await userEvent.click(btn);
    expect(onBookmark).toHaveBeenCalledTimes(1);
    // After click, button title should change to Bookmarked
    expect(screen.getByTitle("Bookmarked")).toBeInTheDocument();
  });

  it("clicking bookmark does NOT call onPreview", async () => {
    const onPreview = vi.fn();
    render(
      <JobCard
        job={makeJob()}
        onApply={vi.fn()}
        onBookmark={vi.fn()}
        onPreview={onPreview}
      />,
    );
    await userEvent.click(screen.getByTitle("Bookmark"));
    expect(onPreview).not.toHaveBeenCalled();
  });
});
