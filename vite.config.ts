import Terminal from "vite-plugin-terminal";
import ViteYaml from "@modyfi/vite-plugin-yaml";
import ui from "@nuxt/ui/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ command }) => ({
  plugins: [
    vue(),
    ui({
      ui: {
        colors: {
          primary: "amber",
          neutral: "stone",
        },
      },
    }),
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
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
}));
