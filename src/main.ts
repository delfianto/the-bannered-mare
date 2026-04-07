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
      worker.events.on("response:mocked", async ({ request, response }) => {
        const url = new URL(request.url);
        const method = request.method;
        const status = response.status;

        console.log(`\n[MSW] ${method} ${url.pathname}${url.search} [${status}]`);

        try {
          const contentType = response.headers.get("content-type");
          if (contentType?.includes("application/json")) {
            const data = await response.clone().json();
            const json = JSON.stringify(data, null, 2);

            if (json.length > 2000) {
              console.log(json.slice(0, 2000) + "\n... [truncated due to size]");
            } else {
              console.log(json);
            }
          }
        } catch {
          // Silent catch for parsing errors
        }
      });
    }

    await worker.start({
      onUnhandledRequest: "bypass",
      quiet: true,
    });

    if (navigator.serviceWorker && !navigator.serviceWorker.controller) {
      console.log("[MSW] Waiting for controller...");
      await new Promise<void>((resolve) => {
        const handler = () => {
          if (navigator.serviceWorker.controller) {
            navigator.serviceWorker.removeEventListener("controllerchange", handler);
            console.log("[MSW] Controller active.");
            resolve();
          }
        };
        navigator.serviceWorker.addEventListener("controllerchange", handler);
      });
    } else {
      console.log("[MSW] Already controlling.");
    }
    return;
  }
}

prepareApp().then(() => {
  app.mount("#app");
});

console.log("Candlekeep initialized...");
