/**
 * Pure date/time formatters shared across views and components. i18n-aware
 * helpers take the caller's `t` as a param (kept pure/testable), mirroring
 * `formatLog.ts`.
 */

type Translator = (key: string, named?: Record<string, unknown>) => string;

/**
 * Format an ISO timestamp through `Intl`. Defaults to a medium date + short
 * time in the runtime locale; pass `options`/`locale` to override (e.g. a long,
 * date-only en-US format). `toLocaleString` with only date components is
 * equivalent to `toLocaleDateString` with the same options.
 */
export function formatDate(
  iso: string,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" },
  locale?: string,
): string {
  return new Date(iso).toLocaleString(locale, options);
}

/**
 * Relative "time ago" phrasing, delegating wording to the caller's i18n `t`.
 * `justNow` (default true) shows "just now" under a minute; `weeks` (default
 * false) rolls days >= 7 up into weeks. The two knobs reproduce each call
 * site's existing bucketing without changing any rendered output.
 */
export function timeAgo(
  iso: string,
  t: Translator,
  options: { justNow?: boolean; weeks?: boolean } = {},
): string {
  const { justNow = true, weeks = false } = options;
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (justNow && mins < 1) return t("time.justNow");
  if (mins < 60) return t("time.minutesAgo", { count: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t("time.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  if (!weeks || days < 7) return t("time.daysAgo", { count: days });
  return t("time.weeksAgo", { count: Math.floor(days / 7) });
}
