import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// Node-side MSW harness for tests — reuses the exact same handler set the
// browser worker serves (src/mocks/browser.ts), so API-coupled composable tests
// exercise the real mocked contract over msw/node instead of monkeypatching
// fetch. Lifecycle (listen/reset/close) is wired in src/test/setup.ts.
export const server = setupServer(...handlers);
