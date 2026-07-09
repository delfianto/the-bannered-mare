import eslintPluginVue from "eslint-plugin-vue";
import tailwind from "eslint-plugin-tailwindcss";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

export default [
  {
    ignores: ["dist/**", "node_modules/**", "bun.lock"],
  },
  ...eslintPluginVue.configs["flat/recommended"],
  {
    files: ["**/*.vue", "**/*.ts"],
    plugins: {
      tailwindcss: tailwind,
      "@typescript-eslint": tsPlugin,
    },
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
      "tailwindcss/classnames-order": "warn",
      "tailwindcss/enforces-shorthand": "warn",
      // Prefer canonical scale classes over equivalent arbitrary values
      // (e.g. text-[0.875rem] -> text-sm). "error" so CI fails on it. Note this
      // rule only catches NAMED scales; dynamic spacing (h-[62px] -> h-15.5) is
      // gated by scripts/canonical-classes.mjs (bun run lint:canonical).
      // (messageId: suggestCanonicalClasses)
      "tailwindcss/no-unnecessary-arbitrary-value": "error",
      "tailwindcss/no-custom-classname": "off",
      "vue/multi-word-component-names": "off",
      "vue/max-attributes-per-line": "off",
      "vue/html-self-closing": "off",
      "vue/singleline-html-element-content-newline": "off",
    },
  },
];
