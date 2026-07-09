#!/usr/bin/env node
/**
 * Canonical Tailwind spacing classes check/fixer.
 *
 * Flags spacing/sizing utilities that use an arbitrary value with a scale
 * equivalent — e.g. `h-[62px]` → `h-15.5`, `w-[400px]` → `w-100`,
 * `w-[16.25rem]` → `w-65`. These are the cases `eslint-plugin-tailwindcss`'s
 * `no-unnecessary-arbitrary-value` rule does NOT catch (it only handles named
 * scales like text-sm / tracking-widest), so they're gated here instead.
 *
 * Why it matters: the app scales the root font-size (Settings → Text Size), so
 * rem-based scale classes grow with the setting while fixed `px` arbitrary
 * values silently don't. See AGENTS.md §6.2.
 *
 *   node scripts/canonical-classes.mjs           # check (exit 1 on violations)
 *   node scripts/canonical-classes.mjs --fix     # rewrite in place
 */
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC = "src";
const FIX = process.argv.includes("--fix");

// Spacing/sizing utilities backed by the rem `--spacing` scale (longest names
// first so `max-w` wins over `w`, etc.).
const PREFIXES = [
  "min-w",
  "min-h",
  "max-w",
  "max-h",
  "gap-x",
  "gap-y",
  "space-x",
  "space-y",
  "inset-x",
  "inset-y",
  "translate-x",
  "translate-y",
  "size",
  "basis",
  "inset",
  "gap",
  "top",
  "right",
  "bottom",
  "left",
  "start",
  "end",
  "px",
  "py",
  "pt",
  "pr",
  "pb",
  "pl",
  "ps",
  "pe",
  "mx",
  "my",
  "mt",
  "mr",
  "mb",
  "ml",
  "ms",
  "me",
  "w",
  "h",
  "p",
  "m",
].join("|");

// boundary, negative, variant chain (sm:/hover:/…), prefix, value, unit
const RE = new RegExp(
  `([\\s"'\`])(-?)((?:[a-z][a-z0-9-]*:)*)(${PREFIXES})-\\[([0-9.]+)(px|rem)\\]`,
  "g",
);

/** px → value/4 (spacing base is 0.25rem = 4px); rem → value/0.25. */
function canonical(value, unit) {
  const n = unit === "px" ? value / 4 : value * 4;
  return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (p.endsWith(".vue")) out.push(p);
  }
  return out;
}

let violations = 0;
let fixedFiles = 0;

for (const file of walk(SRC)) {
  const src = readFileSync(file, "utf8");
  let hits = 0;
  const next = src.replace(RE, (_m, b, neg, variant, prefix, val, unit, offset, full) => {
    hits++;
    if (!FIX) {
      const line = full.slice(0, offset).split("\n").length;
      const old = `${neg}${variant}${prefix}-[${val}${unit}]`;
      const fixed = `${neg}${variant}${prefix}-${canonical(parseFloat(val), unit)}`;
      console.error(`  ${file}:${line}  ${old}  →  ${fixed}`);
    }
    return `${b}${neg}${variant}${prefix}-${canonical(parseFloat(val), unit)}`;
  });
  if (hits) {
    violations += hits;
    if (FIX) {
      writeFileSync(file, next);
      fixedFiles++;
    }
  }
}

if (FIX) {
  console.log(`canonical-classes: fixed ${violations} value(s) across ${fixedFiles} file(s).`);
  process.exit(0);
}

if (violations) {
  console.error(
    `\n✗ ${violations} non-canonical spacing class(es). Use the scale (e.g. h-15.5, not h-[62px]) so they scale with the Text Size setting.` +
      `\n  Run: bun run lint:canonical:fix`,
  );
  process.exit(1);
}
console.log("✓ canonical-classes: all spacing utilities use canonical scale classes.");
