/** Pure formatters for the chat LLM-audit log rows (ChatDrawerLogsTab). */

/** Compact token counts: 1_234 → "1.2k", 12_000 → "12k", 2_000_000 → "2.0M". */
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

/** Latency: <1s in ms, otherwise seconds with 2 decimals. */
export function formatLatency(ms: number): string {
  return ms >= 1_000 ? `${(ms / 1_000).toFixed(2)}s` : `${Math.round(ms)}ms`;
}

/** USD cost: "" when zero/nullish, 4 decimals under $1, else 2. */
export function formatCost(usd: number | null): string {
  if (!usd) return "";
  return usd >= 1 ? `$${usd.toFixed(2)}` : `$${usd.toFixed(4)}`;
}

export function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

type Translator = (key: string, named?: Record<string, unknown>) => string;

/**
 * Relative time for a log's timestamp, delegating the phrasing to the caller's
 * i18n `t` (kept as a param so this stays pure/testable). Falls back to an
 * absolute short date beyond a week.
 */
export function formatLogTime(iso: string, t: Translator): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);
  if (diffMin < 1) return t("time.justNow");
  if (diffMin < 60) return t("time.minutesAgo", { count: diffMin });
  if (diffHr < 24) return t("time.hoursAgo", { count: diffHr });
  if (diffDay < 7) return t("time.daysAgo", { count: diffDay });
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
