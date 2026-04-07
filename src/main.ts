import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

const app = createApp(App);

app.use(createPinia());
app.use(router);

async function prepareApp() {
  const useMocks = import.meta.env.VITE_USE_MOCKS === "true";
  const debugRequest = import.meta.env.VITE_DEBUG_REQUEST === "true";

  if (import.meta.env.DEV && useMocks) {
    const { worker } = await import("./mocks/browser");

    if (debugRequest) {
      worker.events.on("*", (event: any) => {
        const { request, response } = event;
        if (!response || !request) return;
        try {
          const url = new URL(request.url);
          if (!url.pathname.startsWith("/api")) return;
          console.log(`[MSW] ${request.method} ${url.pathname}${url.search} [${response.status}]`);
        } catch {
          // Silent catch
        }
      });
    }

    await worker.start({
      onUnhandledRequest(request, print) {
        const url = new URL(request.url);
        if (url.pathname.startsWith("/api")) {
          print.warning();
        }
      },
      quiet: true,
      serviceWorker: {
        options: {
          // Force the service worker to activate immediately on every page load
          updateViaCache: "none",
        },
      },
    });

    // Wait until service worker is actively controlling the page
    if (navigator.serviceWorker) {
      if (navigator.serviceWorker.controller) {
        console.log("[MSW] Controller active.");
      } else {
        console.log("[MSW] Waiting for controller...");
        await new Promise<void>((resolve) => {
          navigator.serviceWorker.addEventListener("controllerchange", () => {
            console.log("[MSW] Controller active.");
            resolve();
          }, { once: true });
        });
      }
    } else {
      console.log("[MSW] Service Worker API not available, proceeding without wait.");
    }
    return;
  }
}

prepareApp().then(() => {
  app.mount("#app");
});

console.log("Candlekeep initialized...");
