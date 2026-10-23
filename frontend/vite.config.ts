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
      // Preserve mock call history across the Vitest 5 migration.
      clearMocks: false,
      environment: "happy-dom",
      environmentOptions: {
        happyDOM: {
          settings: {
            navigation: { disableMainFrameNavigation: true, disableChildPageNavigation: true },
          },
        },
      },
      globals: false,
      setupFiles: ["./src/test/setup-globals.ts", "./src/test/setup.ts"],
      include: ["src/**/*.{test,spec}.ts"],
      coverage: {
        provider: "v8",
        // Include un-imported product files so coverage reflects the whole app.
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
        reporter: ["text-summary", "json-summary", "html", "lcov"],
        reportOnFailure: true,
        // Whole-app floors include unmounted views; critical state/transport
        // modules also have per-file gates so UI coverage can't mask a regression.
        thresholds: {
          lines: 85,
          statements: 85,
          functions: 85,
          branches: 85,
          "src/components/profiles/ProfileForm.vue": {
            lines: 95,
            statements: 95,
            functions: 95,
            branches: 90,
          },
          "src/composables/useLorebooks.ts": {
            lines: 95,
            statements: 95,
            functions: 95,
            branches: 70,
          },
          "src/composables/usePromptTemplate.ts": {
            lines: 95,
            statements: 95,
            functions: 95,
            branches: 90,
          },
          "src/views/settings/ModelView.vue": {
            lines: 95,
            statements: 90,
            functions: 90,
            branches: 80,
          },
          "src/views/{LorebooksView,SetupWizardView,settings/{ProviderView,PresetView,TemplateView}}.vue":
            {
              perFile: true,
              lines: 85,
              statements: 80,
              functions: 60,
              branches: 55,
            },
          "src/api/client.ts": { lines: 95, statements: 95, functions: 95, branches: 90 },
          "src/stores/*.ts": {
            perFile: true,
            lines: 95,
            statements: 90,
            functions: 95,
            branches: 80,
          },
          "src/composables/use{AssetCache,CharacterForm,ChatMessages,CreateChat,EntityCrud,ListCrud,PaginatedList}.ts":
            {
              perFile: true,
              lines: 95,
              statements: 90,
              functions: 90,
              branches: 80,
            },
        },
      },
    },
  };
});
