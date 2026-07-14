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
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.{test,spec}.ts"],
    },
  };
});
