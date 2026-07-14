// Global harness for component tests. Mirrors main.ts's app wiring so
// `mount()` gets i18n + the three globally-registered primitives without each
// test repeating the setup.
import { config } from "@vue/test-utils";
import { afterAll, afterEach, beforeAll } from "vitest";
import i18n from "@/i18n";
import AppIcon from "@/components/shared/AppIcon.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import AppToggle from "@/components/shared/AppToggle.vue";
import { server } from "@/mocks/server";

config.global.plugins = [i18n];
config.global.components = { AppIcon, SelectMenu, AppToggle };

// Reuse the MSW handler set over msw/node so API-coupled composable tests hit
// real handlers through the unpatched typed client — no fetch monkeypatching.
// `onUnhandledRequest: "error"` turns any endpoint the fixtures don't cover into
// a loud failure instead of a silent network passthrough.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
