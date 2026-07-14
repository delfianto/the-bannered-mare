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

export const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL || "",
  headers: {
    "Content-Type": "application/json",
  },
  fetch: trackedFetch,
});

export class APIError extends Error {
  constructor(
    public statusCode: number,
    public details: unknown,
  ) {
    super(`API Error ${statusCode}`);
    this.name = "APIError";
  }
}
