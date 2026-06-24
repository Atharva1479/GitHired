import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Card } from "@/components/kanban/Card";
import type { Application } from "@/lib/types";

// ── Fixture ───────────────────────────────────────────────────────────────────

const mockApp: Application = {
  id: 1,
  company: "Vercel",
  role: "Software Engineer",
  status: "Applied",
  source: "LinkedIn",
  applied_date: "2026-06-15",
  jd_url: null,
  jd_text: null,
  contact_name: null,
  resume_key: null,
  cover_letter_key: null,
  notes: null,
  fit_score: null,
  created_at: "2026-06-15T00:00:00Z",
  updated_at: "2026-06-15T00:00:00Z",
  soft_deleted: false,
};

function renderCard(overrides: Partial<Application> = {}, props: { dragging?: boolean } = {}) {
  const onOpen = vi.fn();
  const onDragStart = vi.fn();
  const onDragEnd = vi.fn();
  const app = { ...mockApp, ...overrides };

  const { container } = render(
    <Card
      app={app}
      dragging={props.dragging ?? false}
      onOpen={onOpen}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    />,
  );

  const card = container.firstChild as HTMLElement;
  return { card, onOpen, onDragStart, onDragEnd };
}

// ── Render ────────────────────────────────────────────────────────────────────

describe("Card — render", () => {
  it("renders the company name", () => {
    renderCard();
    expect(screen.getByText("Vercel")).toBeInTheDocument();
  });

  it("renders the role", () => {
    renderCard();
    expect(screen.getByText("Software Engineer")).toBeInTheDocument();
  });

  it("renders the first 2 characters as initials (uppercase)", () => {
    renderCard();
    expect(screen.getByText("VE")).toBeInTheDocument();
  });

  it("formats the applied date as 'Mon D'", () => {
    renderCard();
    // 2026-06-15 → "Jun 15"
    expect(screen.getByText("Jun 15")).toBeInTheDocument();
  });

  it("renders the source tag", () => {
    renderCard();
    expect(screen.getByText("LinkedIn")).toBeInTheDocument();
  });

  it("renders fit_score badge when fit_score is set", () => {
    renderCard({ fit_score: 82 });
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("does NOT render fit_score badge when fit_score is null", () => {
    renderCard({ fit_score: null });
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
  });

  it("applies opacity 0.4 when dragging=true", () => {
    const { card } = renderCard({}, { dragging: true });
    expect((card as HTMLElement).style.opacity).toBe("0.4");
  });

  it("applies opacity 1 when dragging=false", () => {
    const { card } = renderCard({}, { dragging: false });
    expect((card as HTMLElement).style.opacity).toBe("1");
  });

  it("root element is draggable", () => {
    const { card } = renderCard();
    expect(card).toHaveAttribute("draggable");
  });
});

// ── Interactions ──────────────────────────────────────────────────────────────

describe("Card — interactions", () => {
  it("calls onOpen when clicked", () => {
    const { card, onOpen } = renderCard();
    fireEvent.click(card);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("calls onDragEnd when drag ends", () => {
    const { card, onDragEnd } = renderCard();
    fireEvent.dragEnd(card);
    expect(onDragEnd).toHaveBeenCalledTimes(1);
  });

  it("calls onDragStart when drag starts", () => {
    const { card, onDragStart } = renderCard();
    // Provide a stub dataTransfer so the component doesn't throw
    const dt = { effectAllowed: "" };
    Object.defineProperty(dt, "effectAllowed", { writable: true, value: "" });
    fireEvent.dragStart(card, { dataTransfer: dt });
    expect(onDragStart).toHaveBeenCalledTimes(1);
  });
});
