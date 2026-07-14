/// <reference types="vitest/config" />
import Terminal from "vite-plugin-terminal";
import ViteYaml from "@modyfi/vite-plugin-yaml";
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite-plus";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ command }) => {
  const useMocks = process.env.VITE_USE_MOCKS === "true";
  console.log(
    `[vite config] VITE_USE_MOCKS=${process.env.VITE_USE_MOCKS}, proxy ${useMocks ? "DISABLED" : "ENABLED"}`,
  );

  return {
    plugins: [
      vue(),
      tailwindcss(),
      ViteYaml(),
      command === "serve" &&
        Terminal({
          console: "terminal",
          output: ["console", "terminal"],
        }),
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      // Disable proxy when using MSW mocks — let the service worker intercept instead
      proxy: useMocks
        ? undefined
        : {
            "/api": {
              target: "http://localhost:8000",
              changeOrigin: true,
            },
            // Admin/observability endpoints live at the server root, not under /api
            "/admin": {
              target: "http://localhost:8000",
              changeOrigin: true,
            },
          },
    },
    // `vp test` (Vitest) reuses this config's vue plugin + `@` alias, so SFCs
    // compile and mount. happy-dom supplies the DOM the UI layer needs.
    test: {
      environment: "happy-dom",
      globals: false,
      setupFiles: ["./src/test/setup-globals.ts", "./src/test/setup.ts"],
      include: ["src/**/*.{test,spec}.ts"],
      coverage: {
        provider: "v8",
        // `all` counts un-imported product files as 0%, so the number reflects
        // real coverage of the app — not just the handful of exercised modules.
        all: true,
        include: ["src/**/*.{ts,vue}"],
        exclude: [
          "src/**/*.{test,spec}.ts",
          "src/test/**",
          "src/mocks/**",
          "src/api/schema.d.ts",
          "src/**/*.d.ts",
          "src/main.ts",
          "src/types/**",
        ],
        reporter: ["text-summary", "json-summary"],
        // Floor ratchets up as coverage lands (Wave 2/3). Set just under the
        // current baseline (lines 2.66 / stmts 2.59 / fns 1.4 / branches 1.69)
        // so CI is honest and catches regressions without being red on day one.
        thresholds: { lines: 2.5, statements: 2.5, functions: 1.3, branches: 1.6 },
      },
    },
  };
});
