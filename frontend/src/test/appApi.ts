import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { characters } from "@/mocks/data/characters";
import { chats } from "@/mocks/data/chats";
import { providers } from "@/mocks/data/providers";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { presets } from "@/mocks/data/presets";
import { profiles } from "@/mocks/data/profiles";
import { personas } from "@/mocks/data/personas";
import { promptTemplates, templateFragments } from "@/mocks/data/prompt-templates";
import { promptFragments } from "@/mocks/data/prompt-fragments";
import { lorebooks } from "@/mocks/data/lorebooks";
import { dataBankEntries } from "@/mocks/data/data-bank";
import { llmLogs } from "@/mocks/data/llm-logs";

type Row = { id: string; [key: string]: unknown };
export function installAppApi() {
  const db = structuredClone({
    characters,
    chats,
    providers,
    models: allModelsMock,
    families: allModelFamiliesMock,
    presets,
    profiles,
    personas,
    templates: promptTemplates,
    fragments: promptFragments,
    lorebooks,
    memories: dataBankEntries,
    logs: llmLogs,
  });
  const requests: {
    method: string;
    path: string;
    query: Record<string, string>;
    body?: unknown;
  }[] = [];
  const record = (request: Request, body?: unknown) => {
    const url = new URL(request.url);
    requests.push({
      method: request.method,
      path: url.pathname,
      query: Object.fromEntries(url.searchParams),
      body,
    });
  };
  const responseFields = (body: object) =>
    Object.fromEntries(
      Object.entries(body).map(([key, value]) => [
        key,
        ["is_default", "is_global", "enabled"].includes(key) && typeof value === "string"
          ? value === "true"
          : value,
      ]),
    );
  const routes: [string, Row[]][] = [
    ["/api/characters", db.characters],
    ["/api/chats", db.chats],
    ["/api/providers", db.providers],
    ["/api/models", db.models],
    ["/api/model-families", db.families],
    ["/api/presets/", db.presets],
    ["/api/profiles/", db.profiles],
    ["/api/personas/", db.personas],
    ["/api/prompt-templates/", db.templates],
    ["/api/prompt-fragments/", db.fragments],
    ["/api/lorebooks", db.lorebooks],
    ["/api/data-bank/", db.memories],
  ];
  for (const [path, rows] of routes) {
    const detail = path.replace(/\/$/, "") + "/:id";
    server.use(
      http.get(path, ({ request }) => {
        record(request);
        const q = new URL(request.url).searchParams;
        const filtered = rows.filter(
          (row) =>
            (!q.has("name__ilike") ||
              String(row.name ?? row.display_name)
                .toLowerCase()
                .includes(q.get("name__ilike")!.toLowerCase())) &&
            (!q.has("scope") || row.scope === q.get("scope")) &&
            (!q.has("enabled") || String(row.enabled) === q.get("enabled")),
        );
        const page = Number(q.get("page") ?? 1),
          limit = Number(q.get("limit") ?? 100);
        const start = (page - 1) * limit;
        return HttpResponse.json({
          items: filtered.slice(start, start + limit),
          meta: {
            total: filtered.length,
            page,
            limit,
            cursor: null,
            has_more: start + limit < filtered.length,
          },
        });
      }),
      http.get(detail, ({ params, request }) => {
        record(request);
        const row = rows.find((r) => r.id === params.id);
        return row
          ? HttpResponse.json(
              path === "/api/models"
                ? { ...row, model_family: db.families.find((f) => f.id === row.model_family_id) }
                : row,
            )
          : HttpResponse.json({ detail: "Not found" }, { status: 404 });
      }),
      http.post(path, async ({ request }) => {
        const contentType = request.headers.get("content-type") ?? "";
        const body = contentType.includes("multipart")
          ? Object.fromEntries(await request.formData())
          : ((await request.json()) as object);
        record(request, body);
        const row = {
          ...rows[0],
          ...responseFields(body),
          id: `created-${requests.length}`,
        } as Row;
        rows.unshift(row);
        return HttpResponse.json(row, { status: 201 });
      }),
      http.put(detail, async ({ request, params }) => {
        const contentType = request.headers.get("content-type") ?? "";
        const body = contentType.includes("multipart")
          ? Object.fromEntries(await request.formData())
          : ((await request.json()) as object);
        record(request, body);
        const index = rows.findIndex((r) => r.id === params.id);
        if (index < 0) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
        rows[index] = { ...rows[index], ...responseFields(body) };
        return HttpResponse.json(rows[index]);
      }),
      http.delete(detail, ({ params, request }) => {
        record(request);
        const i = rows.findIndex((r) => r.id === params.id);
        if (i >= 0) rows.splice(i, 1);
        return new HttpResponse(null, { status: 204 });
      }),
    );
  }
  server.use(
    http.get("/api/model-families/parameter-docs", () => HttpResponse.json({})),
    http.get("/api/prompt-templates/:id/fragments/", ({ params }) =>
      HttpResponse.json({ items: structuredClone(templateFragments.get(String(params.id)) ?? []) }),
    ),
    http.get("/api/providers/:id/models/available", () =>
      HttpResponse.json({ models: [], last_synced_at: null }),
    ),
    http.get("/api/bookmarks/characters", () =>
      HttpResponse.json({ items: db.characters.slice(0, 2) }),
    ),
    http.get("/api/bookmarks/sessions", () => HttpResponse.json({ items: db.chats.slice(0, 2) })),
    http.get("/api/bookmarks/messages", () => HttpResponse.json({ items: [] })),
    http.get("/admin/logs/llm", () =>
      HttpResponse.json({ items: db.logs, meta: { has_more: false, total: db.logs.length } }),
    ),
    http.get("/api/chats/:id/prompt-preview", () =>
      HttpResponse.json({
        parameters: { temperature: 0.8 },
        messages: [{ role: "system", content: "You are a storyteller" }],
        model_display_name: "Test model",
        provider_name: "OpenAI",
        model_identifier: "test-model",
      }),
    ),
    http.get("/api/chats/:id/messages", ({ params }) =>
      HttpResponse.json({
        items: [
          {
            id: "assistant",
            chat_id: params.id,
            role: "assistant",
            content: "Welcome, traveler.",
            active_index: 0,
            created_at: new Date().toISOString(),
          },
        ],
        meta: { has_more: false, cursor: null },
      }),
    ),
  );
  return { db, requests };
}
