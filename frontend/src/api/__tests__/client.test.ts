import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { APIError, client, extractApiError, multipartFetch, streamFetch } from "@/api/client";
import { useServerStatus } from "@/composables/useServerStatus";
import { server } from "@/mocks/server";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  useServerStatus().reportResponse(200);
});

describe("API error normalization", () => {
  it.each([
    [{ detail: "Model is in use" }, "Model is in use"],
    [
      {
        detail: [
          { msg: "Required field", loc: ["body", "name"] },
          null,
          {},
          { msg: "Invalid model" },
        ],
      },
      "Required field; Invalid model",
    ],
    [{ detail: [null, {}] }, "Fallback"],
    [{ detail: {} }, "Fallback"],
    [undefined, "Fallback"],
    [null, "Fallback"],
    ["oops", "Fallback"],
  ])("normalizes %j into a useful message", (body, expected) => {
    const err = extractApiError(body, "Fallback", 422);
    expect(err).toBeInstanceOf(APIError);
    expect(err.message).toBe(expected);
    expect(err.statusCode).toBe(422);
    expect(err.detail).toBe(body);
  });
});

describe("tracked typed client", () => {
  it.each([200, 404, 422, 500, 502, 503, 504])(
    "reports reachability for HTTP %s",
    async (status) => {
      server.use(
        http.get("/api/providers", () =>
          HttpResponse.json(status === 200 ? { items: [] } : { detail: "Unavailable" }, { status }),
        ),
      );
      await client.GET("/api/providers");
      expect(useServerStatus().reachable.value).toBe(![502, 503, 504].includes(status));
    },
  );

  it("reports a network failure and restores reachability on the next HTTP response", async () => {
    server.use(http.get("/api/providers", () => HttpResponse.error()));
    await expect(client.GET("/api/providers")).rejects.toThrow();
    expect(useServerStatus().reachable.value).toBe(false);
    server.use(http.get("/api/providers", () => HttpResponse.json({ items: [] })));
    await client.GET("/api/providers");
    expect(useServerStatus().reachable.value).toBe(true);
  });
});

describe("raw multipart and stream transports", () => {
  it("sends multipart with the API base URL, file and abort signal, without a JSON content-type", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.example.test");
    const fetch = vi.fn(async () => new Response(JSON.stringify({ id: "saved" })));
    vi.stubGlobal("fetch", fetch);
    const body = new FormData();
    const file = new File(["portrait"], "portrait.png", { type: "image/png" });
    body.append("avatar", file);
    const signal = new AbortController().signal;
    expect(await multipartFetch("/api/characters", { method: "POST", body, signal })).toEqual({
      data: { id: "saved" },
    });
    expect(fetch).toHaveBeenCalledWith("https://api.example.test/api/characters", {
      method: "POST",
      body,
      signal,
    });
    expect(body.get("avatar")).toBe(file);
  });

  it.each([true, false])(
    "normalizes rejected multipart responses (JSON body: %s)",
    async (json) => {
      server.use(
        http.post("/api/characters", () =>
          json
            ? HttpResponse.json({ detail: "Invalid image" }, { status: 422 })
            : new HttpResponse("bad gateway", { status: 502 }),
        ),
      );
      const result = await multipartFetch("/api/characters", {
        method: "POST",
        body: new FormData(),
      });
      expect(result.data).toBeUndefined();
      expect(result.error).toBeInstanceOf(APIError);
      expect(result.error).toMatchObject({
        message: json ? "Invalid image" : "Request failed (502)",
        statusCode: json ? 422 : 502,
      });
    },
  );

  it("returns network errors as APIError for multipart callers", async () => {
    server.use(http.post("/api/characters", () => HttpResponse.error()));
    const result = await multipartFetch("/api/characters", {
      method: "POST",
      body: new FormData(),
    });
    expect(result.error).toBeInstanceOf(APIError);
    expect(useServerStatus().reachable.value).toBe(false);
  });

  it("leaves a streaming body unread and forwards headers, base URL and signal", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.example.test");
    const response = new Response("data: [DONE]\n\n");
    const fetch = vi.fn(async () => response);
    vi.stubGlobal("fetch", fetch);
    const init = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"content":"hi"}',
      signal: new AbortController().signal,
    };
    expect(await streamFetch("/api/chats/c/messages?stream=true", init)).toBe(response);
    expect(response.bodyUsed).toBe(false);
    expect(fetch).toHaveBeenCalledWith(
      "https://api.example.test/api/chats/c/messages?stream=true",
      init,
    );
  });

  it("rethrows stream network failures so the caller can clean up generation state", async () => {
    const err = new TypeError("offline");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(err));
    await expect(streamFetch("/api/chats/c/messages", { method: "POST" })).rejects.toBe(err);
    expect(useServerStatus().reachable.value).toBe(false);
  });
});
