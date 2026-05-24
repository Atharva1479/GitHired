import {
  Award,
  Flame,
  HandHeart,
  type LucideIcon,
  Medal,
  Phone,
  Send,
  Sparkles,
  Trophy,
  Users,
} from "lucide-react";

export type AchievementTier = "bronze" | "silver" | "gold" | "platinum";

export type AchievementMeta = {
  code: string;
  title: string;
  description: string;
  tier: AchievementTier;
  icon: LucideIcon;
  group: "volume" | "pipeline" | "streak" | "network" | "comeback";
};

export const ACHIEVEMENT_META: Record<string, AchievementMeta> = {
  first_application: {
    code: "first_application",
    title: "First Application",
    description: "You added your first application. The hardest part is starting.",
    tier: "bronze",
    icon: Sparkles,
    group: "volume",
  },
  apps_10: {
    code: "apps_10",
    title: "10 Applications",
    description: "Ten applications submitted. Volume builds momentum.",
    tier: "bronze",
    icon: Send,
    group: "volume",
  },
  apps_50: {
    code: "apps_50",
    title: "Half Century",
    description: "50 applications. Most people quit before this point.",
    tier: "silver",
    icon: Send,
    group: "volume",
  },
  apps_100: {
    code: "apps_100",
    title: "Centurion",
    description: "100 applications. You're in rare territory now.",
    tier: "gold",
    icon: Trophy,
    group: "volume",
  },
  apps_500: {
    code: "apps_500",
    title: "Marathoner",
    description: "500 applications. Built different.",
    tier: "platinum",
    icon: Trophy,
    group: "volume",
  },
  first_phone_screen: {
    code: "first_phone_screen",
    title: "First Phone Screen",
    description: "A company replied. You're past the resume wall.",
    tier: "silver",
    icon: Phone,
    group: "pipeline",
  },
  first_onsite: {
    code: "first_onsite",
    title: "First Onsite",
    description: "Onsite reached. You're a serious candidate.",
    tier: "gold",
    icon: Award,
    group: "pipeline",
  },
  first_offer: {
    code: "first_offer",
    title: "First Offer",
    description: "An offer. Whatever happens next, savor this.",
    tier: "platinum",
    icon: Trophy,
    group: "pipeline",
  },
  networker_10: {
    code: "networker_10",
    title: "Networker",
    description: "10 referral contacts. The hidden job market opens.",
    tier: "silver",
    icon: Users,
    group: "network",
  },
  networker_50: {
    code: "networker_50",
    title: "Super-Networker",
    description: "50 referral contacts. People know you now.",
    tier: "gold",
    icon: Users,
    group: "network",
  },
  streak_3: {
    code: "streak_3",
    title: "3-Day Streak",
    description: "Three days in a row. Habit forming.",
    tier: "bronze",
    icon: Flame,
    group: "streak",
  },
  streak_7: {
    code: "streak_7",
    title: "Week-long Streak",
    description: "Seven straight days. This is what consistency looks like.",
    tier: "silver",
    icon: Flame,
    group: "streak",
  },
  streak_14: {
    code: "streak_14",
    title: "Fortnight Streak",
    description: "Two weeks straight. Job hunting is your routine now.",
    tier: "silver",
    icon: Flame,
    group: "streak",
  },
  streak_30: {
    code: "streak_30",
    title: "Iron Will",
    description: "30-day streak. You don't break easily.",
    tier: "gold",
    icon: Medal,
    group: "streak",
  },
  streak_100: {
    code: "streak_100",
    title: "Centennial",
    description: "100 days. Top 0.1% of users ever.",
    tier: "platinum",
    icon: Trophy,
    group: "streak",
  },
  comeback_kid: {
    code: "comeback_kid",
    title: "Comeback Kid",
    description: "Returned after a long break. Glad you're back.",
    tier: "bronze",
    icon: HandHeart,
    group: "comeback",
  },
};

export const TIER_CLASSES: Record<
  AchievementTier,
  { ring: string; bg: string; text: string; glow: string }
> = {
  bronze: {
    ring: "ring-amber-300/60",
    bg: "bg-amber-50",
    text: "text-amber-700",
    glow: "shadow-[0_0_24px_rgba(251,191,36,0.35)]",
  },
  silver: {
    ring: "ring-slate-300/70",
    bg: "bg-slate-100",
    text: "text-slate-700",
    glow: "shadow-[0_0_24px_rgba(148,163,184,0.4)]",
  },
  gold: {
    ring: "ring-yellow-400/70",
    bg: "bg-yellow-50",
    text: "text-yellow-700",
    glow: "shadow-[0_0_28px_rgba(234,179,8,0.45)]",
  },
  platinum: {
    ring: "ring-indigo-400/70",
    bg: "bg-gradient-to-br from-indigo-50 to-violet-50",
    text: "text-indigo-700",
    glow: "shadow-[0_0_30px_rgba(99,102,241,0.45)]",
  },
};

export function metaFor(code: string): AchievementMeta {
  return (
    ACHIEVEMENT_META[code] ?? {
      code,
      title: code,
      description: "Achievement unlocked.",
      tier: "bronze",
      icon: Award,
      group: "volume",
    }
  );
}
