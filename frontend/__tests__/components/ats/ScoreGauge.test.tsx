import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ScoreGauge } from "@/components/ats/ScoreGauge";

// ScoreGauge animates via requestAnimationFrame. Fake timers keep tests fast.
beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("ScoreGauge", () => {
  it("renders the grade label", () => {
    render(<ScoreGauge score={80} grade="A" />);
    expect(screen.getByText("Grade A")).toBeInTheDocument();
  });

  it("renders the '/ 100' denominator", () => {
    render(<ScoreGauge score={60} grade="B" />);
    expect(screen.getByText("/ 100")).toBeInTheDocument();
  });

  it("renders an SVG ring", () => {
    const { container } = render(<ScoreGauge score={55} grade="C" />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders grade badge for high score (green tone)", () => {
    const { container } = render(<ScoreGauge score={90} grade="A+" />);
    const badge = screen.getByText("Grade A+");
    // emerald class applied for score ≥ 70
    expect(badge.className).toContain("emerald");
  });

  it("renders grade badge for mid score (amber tone)", () => {
    render(<ScoreGauge score={60} grade="B" />);
    const badge = screen.getByText("Grade B");
    expect(badge.className).toContain("amber");
  });

  it("renders grade badge for low score (red tone)", () => {
    render(<ScoreGauge score={30} grade="D" />);
    const badge = screen.getByText("Grade D");
    expect(badge.className).toContain("red");
  });
});
