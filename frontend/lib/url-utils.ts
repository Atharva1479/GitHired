export function safeUrl(url: string | null | undefined): string {
  if (!url) return "#";
  try {
    const p = new URL(url);
    if (p.protocol === "https:" || p.protocol === "http:") return url;
  } catch {}
  return "#";
}
