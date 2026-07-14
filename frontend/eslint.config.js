import tailwind from "eslint-plugin-tailwindcss";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";

// This ESLint config has ONE job: flag Tailwind arbitrary values that have a
// canonical named scale (e.g. `text-[0.875rem]` -> `text-sm`). JS/Vue linting is
// Oxlint (`vp lint`) and formatting is Oxfmt (`vp fmt`); the vue-recommended
// preset is intentionally NOT pulled in here — its formatting rules
// (`vue/html-indent`, closing-bracket-newline, …) duplicated and fought Oxfmt.
// Dynamic spacing (`h-[62px]` -> `h-15.5`) is gated separately by
// scripts/canonical-classes.mjs (`bun run lint:canonical`).
export default [
  { ignores: ["dist/**", "node_modules/**", "bun.lock"] },
  {
    files: ["**/*.vue", "**/*.ts"],
    plugins: { tailwindcss: tailwind },
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    settings: {
      tailwindcss: {
        cssConfigPath: "src/assets/main.css",
      },
    },
    rules: {
      // The single enforced rule (CI-failing): named-scale canonicalization.
      // Ordering/shorthand are left off so `lint:tailwind` stays silent unless
      // there's a real arbitrary-value violation (no advisory-warning noise).
      "tailwindcss/no-unnecessary-arbitrary-value": "error",
      "tailwindcss/classnames-order": "off",
      "tailwindcss/enforces-shorthand": "off",
      "tailwindcss/no-custom-classname": "off",
    },
  },
];
