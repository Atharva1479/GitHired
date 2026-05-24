// frontend/lib/settings.ts

export type AiProvider = "auto" | "gemini" | "ollama";

export type UserSettings = {
  ai_provider: AiProvider;
  ollama_model: string | null;
  elevenlabs_voice_id: string | null;
  digest_opt_in: boolean;
  /** Hour 0–23 UTC for nudge delivery; null = server default */
  nudge_hour: number | null;
  /** Target applications per week, 1–50 */
  weekly_apps_goal: number;
  wake_word_enabled: boolean;
  auto_brief_enabled: boolean;
};

export type SettingsPatch = Partial<{
  ai_provider: AiProvider;
  ollama_model: string | null;
  elevenlabs_voice_id: string | null;
  digest_opt_in: boolean;
  nudge_hour: number | null;
  weekly_apps_goal: number;
  wake_word_enabled: boolean;
  auto_brief_enabled: boolean;
}>;

export type VoiceOption = {
  id: string;
  name: string;
  description: string;
  gender: "female" | "male";
};

export const VOICE_OPTIONS: VoiceOption[] = [
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella",   description: "Warm & friendly",        gender: "female" },
  { id: "XrExE9yKIg1WjnnlVkGX", name: "Matilda", description: "Friendly American",      gender: "female" },
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam",    description: "Deep American",          gender: "male"   },
  { id: "ErXwobaYiN019PkySvjV", name: "Antoni",  description: "Well-rounded American",  gender: "male"   },
];

/** Voice ID the app ships with when no preference is saved. */
export const DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL";
