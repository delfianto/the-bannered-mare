import createClient from "openapi-fetch";
import { useServerStatus } from "@/composables/useServerStatus";
import type { paths } from "./schema";

const { reportResponse, reportNetworkError } = useServerStatus();

// Every request feeds backend-reachability: a network-level throw (connection
// refused) or an upstream-gateway status (502/503/504 — e.g. the dev proxy when
// the backend is down) marks it unreachable; any other response marks it up.
async function trackedFetch(input: Request): Promise<Response> {
  try {
    const response = await fetch(input);
    reportResponse(response.status);
    return response;
  } catch (err) {
    reportNetworkError();
    throw err;
  }
}

// SSE sends can't go through openapi-fetch (it can't hand back a body reader for
// streaming), so they stay on raw fetch — but route them here so they still get
// the typed client's base URL + reachability reporting instead of silently
// bypassing them.
export async function streamFetch(path: string, init: RequestInit): Promise<Response> {
  const baseUrl = import.meta.env.VITE_API_URL || "";
  try {
    const response = await fetch(`${baseUrl}${path}`, init);
    reportResponse(response.status);
    return response;
  } catch (err) {
    reportNetworkError();
    throw err;
  }
}

export const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL || "",
  headers: {
    "Content-Type": "application/json",
  },
  fetch: trackedFetch,
});

export class APIError extends Error {
  constructor(
    message: string,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Normalize an openapi-fetch error body into an APIError carrying a human
 * message. The backend returns `{ detail: string }` (domain errors) or
 * `{ detail: [{ msg, loc }] }` (HTTPValidationError); pull the message out of
 * either instead of `JSON.stringify`-ing the whole object into a toast. Falls
 * back to `fallback` when there's no usable detail.
 */
export function extractApiError(error: unknown, fallback = "Request failed"): APIError {
  const detail = (error as { detail?: unknown } | null | undefined)?.detail;
  if (typeof detail === "string") {
    return new APIError(detail, error);
  }
  if (Array.isArray(detail)) {
    const msg = detail
      .map((d) =>
        d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : "",
      )
      .filter(Boolean)
      .join("; ");
    return new APIError(msg || fallback, error);
  }
  return new APIError(fallback, error);
}
