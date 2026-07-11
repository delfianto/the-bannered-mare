import { ref } from "vue";

/**
 * Backend reachability, shared app-wide.
 *
 * The API client (`src/api/client.ts`) wraps `fetch` to feed this. "Unreachable"
 * means the backend can't be talked to at all — either a network-level throw
 * (connection refused, e.g. prod hitting a down server directly) or an upstream
 * gateway status (502/503/504, e.g. the dev Vite proxy when :8000 is down). A
 * plain 500 is the server erroring while *reachable*, so it does not trip this.
 * `ServerStatusBanner` renders off `reachable` and calls `checkNow()` to retry/poll.
 */
const reachable = ref(true);
const checking = ref(false);

// Statuses a proxy/gateway returns when it can't reach the upstream backend.
const UNREACHABLE_STATUSES = new Set([502, 503, 504]);

function reportResponse(status: number): void {
  reachable.value = !UNREACHABLE_STATUSES.has(status);
}

function reportNetworkError(): void {
  reachable.value = false;
}

// A cheap proxied endpoint (unlike /health, /api/* is forwarded by the dev proxy).
async function checkNow(): Promise<boolean> {
  checking.value = true;
  try {
    const baseUrl = import.meta.env.VITE_API_URL || "";
    const resp = await fetch(`${baseUrl}/api/providers`, { method: "GET" });
    reportResponse(resp.status);
  } catch {
    reachable.value = false;
  } finally {
    checking.value = false;
  }
  return reachable.value;
}

export function useServerStatus() {
  return { reachable, checking, reportResponse, reportNetworkError, checkNow };
}
