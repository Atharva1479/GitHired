import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { STATUSES } from "@/lib/types";

describe("StatusBadge", () => {
  it("renders every valid status without throwing", () => {
    for (const status of STATUSES) {
      const { unmount } = render(<StatusBadge status={status} />);
      unmount();
    }
  });

  it("displays the correct label for Applied", () => {
    render(<StatusBadge status="Applied" />);
    expect(screen.getByText("Applied")).toBeInTheDocument();
  });

  it("displays the correct label for Offer", () => {
    render(<StatusBadge status="Offer" />);
    expect(screen.getByText("Offer")).toBeInTheDocument();
  });

  it("displays the correct label for Rejected", () => {
    render(<StatusBadge status="Rejected" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("displays the correct label for Ghosted", () => {
    render(<StatusBadge status="Ghosted" />);
    expect(screen.getByText("Ghosted")).toBeInTheDocument();
  });

  it("renders a <span> at the root (chip shape)", () => {
    const { container } = render(<StatusBadge status="Screening" />);
    expect(container.firstChild?.nodeName).toBe("SPAN");
  });

  it("includes an aria-hidden dot element", () => {
    const { container } = render(<StatusBadge status="Interview" />);
    const dot = container.querySelector("[aria-hidden]");
    expect(dot).toBeInTheDocument();
  });
});
