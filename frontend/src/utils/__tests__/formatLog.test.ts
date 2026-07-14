import { describe, it, expect } from "vitest";
import { formatTokens, formatLatency, formatCost, formatJson, formatLogTime } from "../formatLog";

describe("formatTokens", () => {
  it("passes small counts through", () => {
    expect(formatTokens(0)).toBe("0");
    expect(formatTokens(999)).toBe("999");
  });
  it("abbreviates thousands (1 decimal under 10k, 0 at/above)", () => {
    expect(formatTokens(1_234)).toBe("1.2k");
    expect(formatTokens(12_000)).toBe("12k");
  });
  it("abbreviates millions", () => {
    expect(formatTokens(2_000_000)).toBe("2.0M");
  });
});

describe("formatLatency", () => {
  it("uses ms under 1s", () => {
    expect(formatLatency(850)).toBe("850ms");
  });
  it("uses seconds at/above 1s", () => {
    expect(formatLatency(1_500)).toBe("1.50s");
  });
});

describe("formatCost", () => {
  it("is empty for zero/nullish", () => {
    expect(formatCost(0)).toBe("");
    expect(formatCost(null)).toBe("");
  });
  it("uses 4 decimals under $1, 2 at/above", () => {
    expect(formatCost(0.0123)).toBe("$0.0123");
    expect(formatCost(2.5)).toBe("$2.50");
  });
});

describe("formatJson", () => {
  it("pretty-prints with 2-space indent", () => {
    expect(formatJson({ a: 1 })).toBe('{\n  "a": 1\n}');
  });
});

describe("formatLogTime", () => {
  const t = (key: string, named?: Record<string, unknown>) =>
    named ? `${key}:${named.count}` : key;
  it("says just-now under a minute", () => {
    expect(formatLogTime(new Date().toISOString(), t)).toBe("time.justNow");
  });
  it("counts minutes/hours/days via the translator", () => {
    expect(formatLogTime(new Date(Date.now() - 5 * 60_000).toISOString(), t)).toBe(
      "time.minutesAgo:5",
    );
    expect(formatLogTime(new Date(Date.now() - 3 * 3_600_000).toISOString(), t)).toBe(
      "time.hoursAgo:3",
    );
    expect(formatLogTime(new Date(Date.now() - 2 * 86_400_000).toISOString(), t)).toBe(
      "time.daysAgo:2",
    );
  });
});
