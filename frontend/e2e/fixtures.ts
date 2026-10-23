import { test as base, expect, type Request } from "@playwright/test";
import { characters } from "../src/mocks/data/characters";
import { chats } from "../src/mocks/data/chats";
import { profiles } from "../src/mocks/data/profiles";
import { providers } from "../src/mocks/data/providers";
import { allModelsMock } from "../src/mocks/data/models-data";
import { allModelFamiliesMock } from "../src/mocks/data/model-families-data";
import { promptTemplates } from "../src/mocks/data/prompt-templates";
import { presets } from "../src/mocks/data/presets";
import { personas } from "../src/mocks/data/personas";
import type { components } from "../src/api/schema";

type Message = components["schemas"]["MessageResponse"];
const timestamp = "2026-10-23T00:00:00Z";
const portrait = "/e2e-portrait.svg";
const svg =
  '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="100"><rect width="80" height="100" fill="#C9922E"/></svg>';
function createApi() {
  const db = structuredClone({
    characters: characters.slice(0, 2),
    chats: chats.slice(0, 2),
    profiles,
    providers,
    models: allModelsMock,
    families: allModelFamiliesMock,
    templates: promptTemplates,
    presets,
    personas,
  });
  for (const char of db.characters)
    Object.assign(char, { avatar: portrait, avatar_large: portrait, avatar_thumbnail: portrait });
  for (const chat of db.chats)
    Object.assign(chat.character, { avatar: portrait, avatar_thumbnail: portrait });
  const messages = new Map<string, Message[]>();
  const writes: { method: string; path: string; body: Record<string, unknown> }[] = [];
  const rejected = new Set<string>();
  let sequence = 0;
  function history(id: string) {
    if (!messages.has(id))
      messages.set(id, [
        {
          id: `greeting-${id}`,
          chat_id: id,
          role: "assistant",
          content: "Welcome, traveler.",
          active_index: 0,
          created_at: timestamp,
        },
      ]);
    return messages.get(id)!;
  }
  return {
    db,
    writes,
    history,
    rejected,
    failGeneration: false,
    nextId: () => `browser-${++sequence}`,
    rejectNext: (method: string, path: string) => rejected.add(`${method} ${path}`),
  };
}
function characterFields(body: Record<string, unknown>) {
  const { avatar, ...fields } = body;
  if (avatar)
    Object.assign(fields, { avatar: portrait, avatar_large: portrait, avatar_thumbnail: portrait });
  if (fields.version) fields.version = Number(fields.version);
  return fields;
}
type BrowserApi = ReturnType<typeof createApi>;
async function readBody(request: Request): Promise<Record<string, unknown>> {
  const contentType = request.headers()["content-type"] ?? "";
  if (contentType.includes("multipart/form-data")) {
    const form = await new Response(new Uint8Array(request.postDataBuffer()!), {
      headers: { "Content-Type": contentType },
    }).formData();
    return Object.fromEntries(
      Array.from(form.entries(), ([key, value]) => [
        key,
        typeof value === "string" && ["tags", "example_dialogues"].includes(key)
          ? JSON.parse(value)
          : typeof value === "string"
            ? value
            : { name: value.name, type: value.type, size: value.size },
      ]),
    );
  }
  return request.postData() ? request.postDataJSON() : {};
}
export const test = base.extend<{ api: BrowserApi }>({
  api: [
    async ({ page, context, baseURL }, use) => {
      const api = createApi();
      const unexpected: string[] = [];
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await context.route("**/*", async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        const path = url.pathname;
        const method = request.method();
        if (url.origin !== baseURL) {
          if (request.resourceType() === "image")
            return route.fulfill({ contentType: "image/svg+xml", body: svg });
          if (request.resourceType() === "stylesheet")
            return route.fulfill({ contentType: "text/css", body: "" });
          return route.abort("blockedbyclient");
        }
        if (path === portrait) return route.fulfill({ contentType: "image/svg+xml", body: svg });
        if (!path.startsWith("/api/") && !path.startsWith("/admin/")) return route.continue();
        const json = (body: unknown, status = 200) =>
          route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
        const list = (items: unknown[]) =>
          json({
            items,
            meta: { total: items.length, page: 1, limit: 100, has_more: false, cursor: null },
          });
        const body = method === "GET" ? {} : await readBody(request);
        if (method !== "GET") api.writes.push({ method, path, body });
        if (api.rejected.delete(`${method} ${path}`))
          return json({ detail: "Save rejected by test server" }, 422);
        if (method === "GET") {
          if (path === "/api/model-families/parameter-docs") return json({});
          const collections: Record<string, unknown[]> = {
            "/api/characters": api.db.characters,
            "/api/chats": api.db.chats,
            "/api/profiles/": api.db.profiles,
            "/api/providers": api.db.providers,
            "/api/models": api.db.models,
            "/api/model-families": api.db.families,
            "/api/prompt-templates/": api.db.templates,
            "/api/presets/": api.db.presets,
            "/api/personas/": api.db.personas,
            "/api/lorebooks": [],
            "/api/data-bank/": [],
            "/api/bookmarks/characters": [],
            "/api/bookmarks/sessions": [],
            "/api/bookmarks/messages": [],
          };
          if (path in collections) return list(collections[path]);
          const char = api.db.characters.find((c) => path === `/api/characters/${c.id}`);
          if (char) return json(char);
          const chatMessages = path.match(/^\/api\/chats\/([^/]+)\/messages$/);
          if (chatMessages) return list([...api.history(chatMessages[1])].reverse());
        }
        if (path === "/api/characters" && method === "POST") {
          const char = {
            ...api.db.characters[0],
            ...characterFields(body),
            id: api.nextId(),
            created_at: timestamp,
            updated_at: timestamp,
          };
          api.db.characters.unshift(char);
          return json(char, 201);
        }
        const charIndex = api.db.characters.findIndex((c) => path === `/api/characters/${c.id}`);
        if (charIndex >= 0 && method === "PUT") {
          Object.assign(api.db.characters[charIndex], characterFields(body), {
            updated_at: timestamp,
          });
          return json(api.db.characters[charIndex]);
        }
        if (path === "/api/profiles/" && method === "POST") {
          const profile = { ...api.db.profiles[0], ...body, id: api.nextId() };
          api.db.profiles.unshift(profile);
          return json(profile, 201);
        }
        if (path === "/api/chats" && method === "POST") {
          const character = api.db.characters.find((c) => c.id === body.character_id)!;
          const profile = api.db.profiles.find((p) => p.id === body.profile_id)!;
          const chat = {
            ...api.db.chats[0],
            id: api.nextId(),
            title: "Browser tale",
            character: {
              id: character.id,
              name: character.name,
              avatar: portrait,
              avatar_thumbnail: portrait,
            },
            model: { id: profile.model_id!, name: "Test model" },
            last_profile_name: profile.name,
            created_at: timestamp,
            updated_at: timestamp,
          };
          api.db.chats.unshift(chat);
          return json(chat, 201);
        }
        const send = path.match(/^\/api\/chats\/([^/]+)\/messages$/);
        if (send && method === "POST") {
          const id = send[1];
          const history = api.history(id);
          if (!url.searchParams.has("regenerate"))
            history.push({
              id: api.nextId(),
              chat_id: id,
              role: "user",
              content: String(body.content ?? ""),
              active_index: 0,
              created_at: timestamp,
            });
          if (api.failGeneration) {
            api.failGeneration = false;
            return json({ detail: "Provider unavailable" }, 503);
          }
          const reply = {
            id: api.nextId(),
            chat_id: id,
            role: "assistant" as const,
            content: "The archive opens. Your journey begins.",
            active_index: 0,
            created_at: timestamp,
          };
          history.push(reply);
          return route.fulfill({
            contentType: "text/event-stream",
            body:
              [
                { type: "start", message_id: reply.id },
                { type: "text", content: "The archive opens. " },
                { type: "text", content: "Your journey begins." },
              ]
                .map((event) => `data: ${JSON.stringify(event)}\n\n`)
                .join("") + "data: [DONE]\n\n",
          });
        }
        if (path.endsWith("/messages/suggestions") && method === "POST")
          return json({
            suggestions:
              body.mode === "impersonate" ? ["I seek forgotten knowledge."] : ["Curious", "Bold"],
          });
        unexpected.push(`${method} ${path}`);
        return json({ detail: `Unhandled browser fixture: ${method} ${path}` }, 501);
      });
      await use(api);
      expect(unexpected, "Every API endpoint must have an explicit fixture").toEqual([]);
      expect(errors, "Uncaught browser errors").toEqual([]);
    },
    { auto: true },
  ],
});
export { expect } from "@playwright/test";
