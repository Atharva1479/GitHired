export type Rank = {
  tier: "bronze" | "silver" | "gold" | "platinum" | "diamond" | "master";
  title: string;
  min: number;
  max: number;
  badge: string; // tailwind classes for the level pill
  ring: string;  // tailwind ring classes
};

export const RANKS: Rank[] = [
  {
    tier: "bronze",
    title: "Bronze Rookie",
    min: 1,
    max: 4,
    badge: "bg-amber-100 text-amber-700 ring-amber-200",
    ring: "ring-amber-300",
  },
  {
    tier: "silver",
    title: "Silver Hunter",
    min: 5,
    max: 9,
    badge: "bg-slate-100 text-slate-700 ring-slate-200",
    ring: "ring-slate-300",
  },
  {
    tier: "gold",
    title: "Gold Closer",
    min: 10,
    max: 19,
    badge: "bg-yellow-100 text-yellow-800 ring-yellow-200",
    ring: "ring-yellow-300",
  },
  {
    tier: "platinum",
    title: "Platinum Operator",
    min: 20,
    max: 29,
    badge: "bg-indigo-100 text-indigo-700 ring-indigo-200",
    ring: "ring-indigo-300",
  },
  {
    tier: "diamond",
    title: "Diamond Ace",
    min: 30,
    max: 49,
    badge: "bg-cyan-100 text-cyan-700 ring-cyan-200",
    ring: "ring-cyan-300",
  },
  {
    tier: "master",
    title: "Master",
    min: 50,
    max: 9999,
    badge:
      "bg-gradient-to-br from-fuchsia-100 to-indigo-100 text-fuchsia-700 ring-fuchsia-200",
    ring: "ring-fuchsia-300",
  },
];

export function rankForLevel(level: number): Rank {
  for (const r of RANKS) {
    if (level >= r.min && level <= r.max) return r;
  }
  return RANKS[0];
}
