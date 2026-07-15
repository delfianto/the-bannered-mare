import { describe, it, expect } from "vitest";
import { formatDate, timeAgo } from "../date";

describe("formatDate", () => {
  const iso = "2024-01-15T09:05:00Z";

  it("reproduces the settings views' medium-date + short-time default", () => {
    // The 6 settings/detail views formatted inline as
    // `toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })`.
    expect(formatDate(iso)).toBe(
      new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }),
    );
  });

  it("reproduces CharacterDetailView's long date-only en-US format", () => {
    // Previously `toLocaleDateString("en-US", { year, month, day })`; the util
    // routes through `toLocaleString`, which is equivalent for date-only options.
    const opts: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    expect(formatDate(iso, opts, "en-US")).toBe(new Date(iso).toLocaleDateString("en-US", opts));
    expect(formatDate(iso, opts, "en-US")).toBe("January 15, 2024");
  });
});

describe("timeAgo", () => {
  // Mirrors formatLog.test.ts: a fake translator echoes key + count so the
  // bucketing is asserted without depending on the real i18n catalog.
  const t = (key: string, named?: Record<string, unknown>) =>
    named ? `${key}:${named.count}` : key;

  const agoIso = (ms: number) => new Date(Date.now() - ms).toISOString();
  const MIN = 60_000;
  const HOUR = 3_600_000;
  const DAY = 86_400_000;

  it("says just-now under a minute by default (variant B)", () => {
    expect(timeAgo(agoIso(0), t)).toBe("time.justNow");
  });

  it("counts minutes / hours / days via the translator", () => {
    expect(timeAgo(agoIso(5 * MIN), t)).toBe("time.minutesAgo:5");
    expect(timeAgo(agoIso(3 * HOUR), t)).toBe("time.hoursAgo:3");
    expect(timeAgo(agoIso(2 * DAY), t)).toBe("time.daysAgo:2");
  });

  it("keeps days unbounded when weeks is off (default)", () => {
    expect(timeAgo(agoIso(10 * DAY), t)).toBe("time.daysAgo:10");
  });

  it("omits just-now and rolls into weeks for the Bookmarks bucketing", () => {
    // BookmarksView uniquely drops the just-now guard and adds a weeks bucket.
    expect(timeAgo(agoIso(0), t, { justNow: false, weeks: true })).toBe("time.minutesAgo:0");
    expect(timeAgo(agoIso(3 * DAY), t, { justNow: false, weeks: true })).toBe("time.daysAgo:3");
    expect(timeAgo(agoIso(10 * DAY), t, { justNow: false, weeks: true })).toBe("time.weeksAgo:1");
  });
});
