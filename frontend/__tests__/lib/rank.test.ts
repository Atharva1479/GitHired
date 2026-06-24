import { describe, expect, it } from "vitest";

import { RANKS, rankForLevel } from "@/lib/rank";

describe("RANKS", () => {
  it("covers a contiguous range from 1 to 9999", () => {
    // Every integer 1..9999 must be covered by exactly one rank
    const sorted = [...RANKS].sort((a, b) => a.min - b.min);
    expect(sorted[0].min).toBe(1);
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i].min).toBe(sorted[i - 1].max + 1);
    }
    expect(sorted[sorted.length - 1].max).toBeGreaterThanOrEqual(9999);
  });

  it("each rank has required display fields", () => {
    for (const r of RANKS) {
      expect(r.tier).toBeTruthy();
      expect(r.title).toBeTruthy();
      expect(r.badge).toBeTruthy();
      expect(r.ring).toBeTruthy();
    }
  });
});

describe("rankForLevel", () => {
  it("level 1 → bronze", () => {
    expect(rankForLevel(1).tier).toBe("bronze");
  });

  it("level 4 → bronze (upper boundary)", () => {
    expect(rankForLevel(4).tier).toBe("bronze");
  });

  it("level 5 → silver (next tier starts)", () => {
    expect(rankForLevel(5).tier).toBe("silver");
  });

  it("level 9 → silver (upper boundary)", () => {
    expect(rankForLevel(9).tier).toBe("silver");
  });

  it("level 10 → gold", () => {
    expect(rankForLevel(10).tier).toBe("gold");
  });

  it("level 19 → gold (upper boundary)", () => {
    expect(rankForLevel(19).tier).toBe("gold");
  });

  it("level 20 → platinum", () => {
    expect(rankForLevel(20).tier).toBe("platinum");
  });

  it("level 29 → platinum (upper boundary)", () => {
    expect(rankForLevel(29).tier).toBe("platinum");
  });

  it("level 30 → diamond", () => {
    expect(rankForLevel(30).tier).toBe("diamond");
  });

  it("level 49 → diamond (upper boundary)", () => {
    expect(rankForLevel(49).tier).toBe("diamond");
  });

  it("level 50 → master", () => {
    expect(rankForLevel(50).tier).toBe("master");
  });

  it("level 999 → master (unbounded top tier)", () => {
    expect(rankForLevel(999).tier).toBe("master");
  });

  it("returns a Rank with a non-empty title at every boundary", () => {
    for (const boundary of [1, 4, 5, 9, 10, 19, 20, 29, 30, 49, 50]) {
      expect(rankForLevel(boundary).title).toBeTruthy();
    }
  });

  it("falls back gracefully for level 0 (returns RANKS[0])", () => {
    const result = rankForLevel(0);
    expect(result).toBe(RANKS[0]);
  });
});
