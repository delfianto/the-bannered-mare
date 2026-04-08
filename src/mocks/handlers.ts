import { http, HttpResponse, delay } from "msw";
import { characters } from "@/mocks/data/characters";
import { chats } from "@/mocks/data/chats";
import { providers } from "@/mocks/data/providers";
import { allModelsMock } from "@/mocks/data/models-data";
import { personas } from "@/mocks/data/personas";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { modelFamiliesParameterDocs } from "@/mocks/data/model-parameters";
import { dataBankEntries } from "@/mocks/data/data-bank";
import { presets } from "@/mocks/data/presets";
import { promptTemplates, templateFragments } from "@/mocks/data/prompt-templates";
import { promptFragments } from "@/mocks/data/prompt-fragments";
import { lorebooks } from "@/mocks/data/lorebooks";
import { conversationCache } from "@/mocks/loader";
import "@/mocks/data/messages"; // Initialize registrations
import type { components } from "@/api/schema";

type Chat = components["schemas"]["ChatResponse"];
type Character = components["schemas"]["CharacterResponse"];
type DataBankEntry = components["schemas"]["DataBankResponse"];
type Persona = components["schemas"]["PersonaResponse"];
type LorebookDetail = components["schemas"]["LorebookDetailResponse"];
type LoreEntryResponse = components["schemas"]["LoreEntryResponse"];

type TemplateFragmentResponse = components["schemas"]["TemplateFragmentResponse"];

const db = {
  characters,
  chats,
  providers,
  allModelsMock,
  personas,
  allModelFamiliesMock,
  dataBankEntries,
  presets,
  promptTemplates,
  promptFragments,
  templateFragments,
  lorebooks,
};

export const handlers = [
  // Health check
  http.get("/api/health", () => {
    return HttpResponse.json({ status: "ok", timestamp: new Date().toISOString() });
  }),

  // Characters
  http.get("/api/characters", async () => {
    await delay(150);
    return HttpResponse.json({
      items: db.characters,
      meta: {
        limit: 100, // Assuming default limit
        has_more: false,
        total: db.characters.length,
        page: 1,
      },
    });
  }),

  http.get("/api/characters/:id", async ({ params }) => {
    const char = db.characters.find((c) => c.id === params.id);
    if (!char) return new HttpResponse(null, { status: 404 });
    await delay(150);
    return HttpResponse.json(char);
  }),

  http.post("/api/characters", async ({ request }) => {
    await delay(200);
    const formData = await request.formData();

    const name = formData.get("name") as string;
    if (!name) {
      return HttpResponse.json({ detail: "name is required" }, { status: 422 });
    }

    const slugName = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
    const id = `${Date.now()}-${slugName}`;

    const tagsRaw = formData.get("tags") as string | null;
    const dialoguesRaw = formData.get("example_dialogues") as string | null;
    const avatarValue = formData.get("avatar") as string | null;

    const newChar: Character = {
      id,
      name,
      description: (formData.get("description") as string) || null,
      personality: (formData.get("personality") as string) || null,
      first_message: (formData.get("first_message") as string) || null,
      example_dialogues: dialoguesRaw ? JSON.parse(dialoguesRaw) : [],
      scenario: (formData.get("scenario") as string) || null,
      post_history_instructions: (formData.get("post_history_instructions") as string) || null,
      alternate_greetings: null,
      tags: tagsRaw ? JSON.parse(tagsRaw) : [],
      gender: (formData.get("gender") as Character["gender"]) || null,
      custom_gender: (formData.get("custom_gender") as string) || null,
      creator: (formData.get("creator") as string) || null,
      version: Number(formData.get("version")) || 1,
      avatar: avatarValue || null,
      avatar_thumbnail: avatarValue || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    db.characters.unshift(newChar);
    return HttpResponse.json(newChar, { status: 201 });
  }),

  http.put("/api/characters/:id", async ({ params, request }) => {
    await delay(200);
    const charIndex = db.characters.findIndex((c) => c.id === params.id);
    if (charIndex === -1) return new HttpResponse(null, { status: 404 });

    const formData = await request.formData();
    const existing = db.characters[charIndex];

    const getString = (key: string) => {
      const val = formData.get(key);
      return val !== null ? (val as string) : undefined;
    };

    const nameVal = getString("name");
    if (nameVal !== undefined) existing.name = nameVal;

    const descVal = getString("description");
    if (descVal !== undefined) existing.description = descVal || null;

    const persVal = getString("personality");
    if (persVal !== undefined) existing.personality = persVal || null;

    const fmVal = getString("first_message");
    if (fmVal !== undefined) existing.first_message = fmVal || null;

    const scenVal = getString("scenario");
    if (scenVal !== undefined) existing.scenario = scenVal || null;

    const phiVal = getString("post_history_instructions");
    if (phiVal !== undefined) existing.post_history_instructions = phiVal || null;

    const genderVal = getString("gender");
    if (genderVal !== undefined) existing.gender = (genderVal as any) || null;

    const customGenderVal = getString("custom_gender");
    if (customGenderVal !== undefined) existing.custom_gender = customGenderVal || null;

    const creatorVal = getString("creator");
    if (creatorVal !== undefined) existing.creator = creatorVal || null;

    const tagsRaw = getString("tags");
    if (tagsRaw !== undefined) existing.tags = tagsRaw ? JSON.parse(tagsRaw) : [];

    const dialoguesRaw = getString("example_dialogues");
    if (dialoguesRaw !== undefined)
      existing.example_dialogues = dialoguesRaw ? JSON.parse(dialoguesRaw) : [];

    const avatarValue = formData.get("avatar") as string | null;
    if (avatarValue !== null) {
      existing.avatar = avatarValue;
      existing.avatar_thumbnail = avatarValue;
    }

    existing.updated_at = new Date().toISOString();
    db.characters[charIndex] = existing;

    return HttpResponse.json(existing);
  }),

  http.delete("/api/characters/:id", async ({ params }) => {
    await delay(200);
    const charIndex = db.characters.findIndex((c) => c.id === params.id);
    if (charIndex === -1) return new HttpResponse(null, { status: 404 });
    db.characters.splice(charIndex, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // Chats
  http.get("/api/chats", async ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") || "20", 10);
    const cursor = url.searchParams.get("cursor") || undefined;

    await delay(200);

    // Sort chats by updated_at descending
    const allChats = [...db.chats].sort((a, b) => {
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });

    let startIndex = 0;
    if (cursor) {
      // Find the index of the chat with updated_at <= cursor
      // (Simplified logic: find the first chat with updated_at < cursor)
      const cursorDate = new Date(cursor).getTime();
      startIndex = allChats.findIndex((chat) => new Date(chat.updated_at).getTime() < cursorDate);
      if (startIndex === -1) startIndex = allChats.length;
    }

    const paginatedChats = allChats.slice(startIndex, startIndex + limit);
    const hasMore = startIndex + limit < allChats.length;
    const nextCursor = hasMore ? paginatedChats[paginatedChats.length - 1].updated_at : null;

    return HttpResponse.json({
      items: paginatedChats,
      meta: {
        limit,
        has_more: hasMore,
        cursor: nextCursor,
        total: allChats.length,
      },
    });
  }),

  http.post("/api/chats", async ({ request }) => {
    const body = (await request.json()) as any;

    // Find character to populate avatar fields
    const character = db.characters.find((c) => c.id === body.character_id);

    const newChat: Chat = {
      id: `chat-${Date.now()}`,
      character: {
        id: body.character_id,
        name: character?.name || "Unknown",
        avatar: character?.avatar || null,
        avatar_thumbnail: character?.avatar_thumbnail || null,
      },
      model: {
        id: body.model_id || "model-1",
        name: "Mock Model",
      },
      title: body.title || "New Conversation",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    db.chats.unshift(newChat);
    // Note: For new chats, there's no need to initialize in conversationCache
    // as it will be handled by the dynamic import when messages are requested
    await delay(400);
    return HttpResponse.json(newChat);
  }),

  http.get("/api/chats/:chatId", async ({ params }) => {
    const chat = db.chats.find((c) => c.id === params.chatId);
    if (!chat) return new HttpResponse(null, { status: 404 });
    await delay(150);
    return HttpResponse.json(chat);
  }),

  // Update chat (title, model)
  http.put("/api/chats/:chatId", async ({ params, request }) => {
    const chat = db.chats.find((c) => c.id === params.chatId);
    if (!chat) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    if (body.title !== undefined) chat.title = body.title;
    if (body.model_id !== undefined) {
      const model = db.allModelsMock.find((m) => m.id === body.model_id);
      if (model) chat.model = { id: model.id, name: model.name };
    }
    chat.updated_at = new Date().toISOString();
    await delay(150);
    return HttpResponse.json(chat);
  }),

  // Delete chat
  http.delete("/api/chats/:chatId", async ({ params }) => {
    const idx = db.chats.findIndex((c) => c.id === params.chatId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.chats.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // Messages endpoint with lazy loading and cursor-based pagination
  http.get("/api/chats/:chatId/messages", async ({ params, request }) => {
    const chatId = params.chatId as string;
    const url = new URL(request.url);

    const limit = parseInt(url.searchParams.get("limit") || "20", 10);
    const cursor = url.searchParams.get("cursor") || undefined;

    if (!conversationCache.has(chatId)) {
      const chatExists = db.chats.find((c) => c.id === chatId);
      if (chatExists) {
        await delay(100);
        const mockMsg = {
          id: `msg-default-${chatId}`,
          chat_id: chatId,
          role: "assistant" as const,
          content: `[Mock] This conversation with ${chatExists.title} hasn't been implemented in YAML yet. This is a placeholder message.`,
          created_at: new Date().toISOString(),
        };
        return HttpResponse.json({
          items: [mockMsg],
          meta: {
            limit,
            has_more: false,
            cursor: null,
            total: 1,
            page: 1,
          },
        });
      }

      await delay(100);
      return HttpResponse.json({
        items: [],
        meta: {
          limit,
          has_more: false,
          cursor: null,
          total: 0,
          page: 1,
        },
      });
    }

    await delay(100);

    const result = await conversationCache.getCursorPaginated(chatId, limit, cursor);

    if (!result) {
      return HttpResponse.json({
        items: [],
        meta: {
          limit,
          has_more: false,
          cursor: null,
        },
      });
    }

    return HttpResponse.json({
      items: result.messages,
      meta: {
        limit,
        has_more: result.hasMore,
        cursor: result.hasMore ? result.messages[result.messages.length - 1]?.created_at : null, // Cursor is the timestamp of the oldest message in the batch
      },
    });
  }),

  // Unified Post message handler (Streaming + Regular + Regenerate)
  http.post("/api/chats/:chatId/messages", async ({ params, request }) => {
    const chatId = params.chatId as string;
    const url = new URL(request.url);
    const stream = url.searchParams.get("stream") === "true";
    const regenerate = url.searchParams.get("regenerate") === "true";

    const chat = db.chats.find((c) => c.id === chatId);
    if (chat) {
      chat.updated_at = new Date().toISOString();
    }

    if (stream) {
      const encoder = new TextEncoder();
      const responseStream = new ReadableStream({
        async start(controller) {
          const text = regenerate
            ? "[Mock Regenerated Response] This is a simulated regenerated reply."
            : "[Mock Streaming AI Response] This is a simulated streaming reply.";
          const words = text.split(" ");

          for (const word of words) {
            const chunk = JSON.stringify({ text: word + " " });
            controller.enqueue(encoder.encode(`data: ${chunk}\n\n`));
            await new Promise((r) => setTimeout(r, 50));
          }

          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          controller.close();
        },
      });

      return new HttpResponse(responseStream, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    } else {
      const body = (await request.json()) as any;
      await delay(800);

      const aiMsg = {
        id: `msg-${Date.now() + 1}`,
        chat_id: chatId,
        role: "assistant" as const,
        content: `[Mock AI Response] You said: "${body?.content}". This is a simulated reply.`,
        created_at: new Date(Date.now() + 1).toISOString(),
      };

      return HttpResponse.json(aiMsg);
    }
  }),

  // Edit message content
  http.put("/api/chats/:chatId/messages/:messageId", async ({ params, request }) => {
    const body = (await request.json()) as any;
    await delay(150);
    return HttpResponse.json({
      id: params.messageId as string,
      chat_id: params.chatId as string,
      role: "user" as const,
      content: body.content || "",
      active_index: 0,
      created_at: new Date().toISOString(),
    });
  }),

  // List message alternatives (swipes)
  http.get("/api/chats/:chatId/messages/:messageId/alternatives", async ({ params }) => {
    await delay(100);
    // Return 2 mock alternatives for any message
    return HttpResponse.json([
      {
        id: `alt-1-${params.messageId}`,
        message_id: params.messageId as string,
        content: "[Alternative 1] The ancient tome reveals a different path — one shrouded in mystery, where the shadows speak louder than the light.",
        token_count: 42,
        ordinal: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: `alt-2-${params.messageId}`,
        message_id: params.messageId as string,
        content: "[Alternative 2] She pauses, reconsidering her words. \"Perhaps there is another way to interpret the runes — one the scholars overlooked.\"",
        token_count: 38,
        ordinal: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  }),

  // Activate a message alternative
  http.put("/api/chats/:chatId/messages/:messageId/alternatives/:alternativeId/activate", async ({ params }) => {
    await delay(100);
    return HttpResponse.json({
      id: params.messageId as string,
      chat_id: params.chatId as string,
      role: "assistant" as const,
      content: "[Swipe activated] The alternative response is now the active one.",
      active_index: 1,
      created_at: new Date().toISOString(),
    });
  }),

  // Prefetch endpoint (optional)
  http.post("/api/chats/:chatId/prefetch", async ({ params }) => {
    const chatId = params.chatId as string;

    if (!conversationCache.has(chatId)) {
      return new HttpResponse(null, { status: 404 });
    }

    conversationCache.preload(chatId).catch(console.error);

    return HttpResponse.json({ status: "prefetching" });
  }),

  // Cache management endpoint (optional, for debugging)
  http.post("/api/cache/clear", async ({ request }) => {
    const body = (await request.json()) as any;
    const chatId = body?.chatId;

    conversationCache.clearCache(chatId);

    return HttpResponse.json({
      status: "cleared",
      stats: conversationCache.getStats(),
    });
  }),

  // Health check with cache stats
  http.get("/api/health", () => {
    return HttpResponse.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      cache_stats: conversationCache.getStats(),
    });
  }),

  // LLM Providers
  http.get("/api/providers", async () => {
    await delay(100);
    return HttpResponse.json(db.providers);
  }),

  // Provider detail
  http.get("/api/providers/:providerId", async ({ params }) => {
    const provider = db.providers.find((p) => p.id === params.providerId);
    if (!provider) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(provider);
  }),

  // Update provider
  http.put("/api/providers/:providerId", async ({ params, request }) => {
    const provider = db.providers.find((p) => p.id === params.providerId);
    if (!provider) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    if (body.name !== undefined) provider.name = body.name;
    if (body.base_url !== undefined) provider.base_url = body.base_url;
    if (body.enabled !== undefined) provider.enabled = body.enabled;
    provider.updated_at = new Date().toISOString();
    await delay(200);
    return HttpResponse.json(provider);
  }),

  // Toggle provider enabled
  http.patch("/api/providers/:providerId/flags", async ({ params, request }) => {
    const provider = db.providers.find((p) => p.id === params.providerId);
    if (!provider) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    if (body.enabled !== undefined) provider.enabled = body.enabled;
    provider.updated_at = new Date().toISOString();
    await delay(100);
    return HttpResponse.json(provider);
  }),

  // Models List
  http.get("/api/models", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const nameParam = url.searchParams.get("name") || url.searchParams.get("name__ilike");
    const providerParam = url.searchParams.get("provider_id");
    const limit = parseInt(url.searchParams.get("limit") || "12", 10);
    const page = parseInt(url.searchParams.get("page") || "1", 10);

    let items = [...db.allModelsMock];
    if (nameParam) {
      const q = nameParam.toLowerCase();
      items = items.filter((m) => m.name.toLowerCase().includes(q));
    }
    if (providerParam) {
      items = items.filter((m) => m.provider_id === providerParam);
    }

    const total = items.length;
    const totalPages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const paged = items.slice(start, start + limit);

    return HttpResponse.json({
      items: paged,
      meta: { total, page, limit, has_more: page < totalPages },
    });
  }),

  // Models Detail (Joined with Model Family)
  http.get("/api/models/:modelId", async ({ params }) => {
    const modelId = params.modelId as string;

    // Find the model in the raw data
    const foundModel = db.allModelsMock.find((m) => m.id === modelId);

    if (!foundModel) {
      return new HttpResponse(null, { status: 404 });
    }

    // Perform relational lookup for the Model Family
    const family = db.allModelFamiliesMock.find((f) => f.id === foundModel.model_family_id);

    // Construct the response with the nested family object
    const responseData = {
      ...foundModel,
      model_family: family || null, // Should ideally always exist if data is consistent
    };

    await delay(100);
    return HttpResponse.json(responseData);
  }),

  // Update model
  http.put("/api/models/:modelId", async ({ params, request }) => {
    const model = db.allModelsMock.find((m) => m.id === params.modelId);
    if (!model) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    for (const key of [
      "name",
      "model_identifier",
      "provider_id",
      "model_family_id",
      "openrouter_identifier",
      "use_openrouter",
      "parameters",
      "enabled",
      "template_id",
    ]) {
      if (body[key] !== undefined) (model as any)[key] = body[key];
    }
    model.updated_at = new Date().toISOString();
    const family = db.allModelFamiliesMock.find((f) => f.id === model.model_family_id);
    await delay(200);
    return HttpResponse.json({ ...model, model_family: family || null });
  }),

  // Toggle model flags
  http.patch("/api/models/:modelId/flags", async ({ params, request }) => {
    const model = db.allModelsMock.find((m) => m.id === params.modelId);
    if (!model) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    if (body.enabled !== undefined) model.enabled = body.enabled;
    if (body.use_openrouter !== undefined) model.use_openrouter = body.use_openrouter;
    model.updated_at = new Date().toISOString();
    await delay(100);
    return HttpResponse.json(model);
  }),

  // Delete model
  http.delete("/api/models/:modelId", async ({ params }) => {
    const idx = db.allModelsMock.findIndex((m) => m.id === params.modelId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.allModelsMock.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // Personas
  http.get("/api/personas/", async () => {
    await delay(100);
    return HttpResponse.json({
      items: db.personas,
      meta: {
        limit: 50,
        has_more: false,
        total: db.personas.length,
        page: 1,
      },
    });
  }),

  http.get("/api/personas/:personaId", async ({ params }) => {
    const persona = db.personas.find((p) => p.id === params.personaId);
    if (!persona) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(persona);
  }),

  // Model Families List
  http.get("/api/model-families", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const nameParam = url.searchParams.get("name");
    const limit = parseInt(url.searchParams.get("limit") || "12", 10);
    const page = parseInt(url.searchParams.get("page") || "1", 10);

    let items = [...db.allModelFamiliesMock];
    if (nameParam) {
      const q = nameParam.toLowerCase();
      items = items.filter((f) => f.name.toLowerCase().includes(q));
    }

    const total = items.length;
    const totalPages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const paged = items.slice(start, start + limit);

    return HttpResponse.json({
      items: paged,
      meta: { total, page, limit, has_more: page < totalPages },
    });
  }),

  // Model Families Detail
  http.get("/api/model-families/parameter-docs", async () => {
    await delay(50);
    return HttpResponse.json(modelFamiliesParameterDocs);
  }),

  http.get("/api/model-families/:id", async ({ params }) => {
    const id = params.id as string;
    const family = db.allModelFamiliesMock.find((f) => f.id === id);

    if (!family) {
      return new HttpResponse(null, { status: 404 });
    }

    await delay(100);
    return HttpResponse.json(family);
  }),

  // Update model family
  http.put("/api/model-families/:id", async ({ params, request }) => {
    const family = db.allModelFamiliesMock.find((f) => f.id === params.id);
    if (!family) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    for (const key of [
      "name",
      "family_identifier",
      "description",
      "provider_types",
      "parameters",
      "unsupported_parameters",
      "extra_metadata",
    ]) {
      if (body[key] !== undefined) (family as any)[key] = body[key];
    }
    family.updated_at = new Date().toISOString();
    await delay(200);
    return HttpResponse.json(family);
  }),

  // Delete model family
  http.delete("/api/model-families/:id", async ({ params }) => {
    const idx = db.allModelFamiliesMock.findIndex((f) => f.id === params.id);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.allModelFamiliesMock.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Data Bank ──────────────────────────────────────────────

  http.get("/api/data-bank/", async ({ request }) => {
    const url = new URL(request.url);
    const scope = url.searchParams.get("scope");

    await delay(150);

    let items = [...db.dataBankEntries];
    if (scope) {
      items = items.filter((e) => e.scope === scope);
    }

    return HttpResponse.json(items);
  }),

  http.post("/api/data-bank/", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["DataBankCreate"];
    await delay(200);

    const newEntry: DataBankEntry = {
      id: `db-entry-${Date.now()}`,
      name: body.name,
      content: body.content,
      scope: body.scope || "global",
      character_id: body.character_id ?? null,
      chat_id: body.chat_id ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    db.dataBankEntries.unshift(newEntry);
    return HttpResponse.json(newEntry, { status: 201 });
  }),

  http.get("/api/data-bank/:entryId", async ({ params }) => {
    const entry = db.dataBankEntries.find((e) => e.id === params.entryId);
    if (!entry) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(entry);
  }),

  http.put("/api/data-bank/:entryId", async ({ params, request }) => {
    const entry = db.dataBankEntries.find((e) => e.id === params.entryId);
    if (!entry) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as components["schemas"]["DataBankUpdate"];

    if (body.name !== undefined && body.name !== null) entry.name = body.name;
    if (body.content !== undefined && body.content !== null) entry.content = body.content;
    if (body.scope !== undefined && body.scope !== null) entry.scope = body.scope;
    entry.updated_at = new Date().toISOString();

    await delay(200);
    return HttpResponse.json(entry);
  }),

  http.delete("/api/data-bank/:entryId", async ({ params }) => {
    const idx = db.dataBankEntries.findIndex((e) => e.id === params.entryId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.dataBankEntries.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Presets ────────────────────────────────────────────────

  http.get("/api/presets/", async ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") || "12", 10);
    const page = parseInt(url.searchParams.get("page") || "1", 10);

    await delay(150);

    const items = [...db.presets];
    const total = items.length;
    const totalPages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const paged = items.slice(start, start + limit);

    return HttpResponse.json({
      items: paged,
      meta: { total, page, limit, has_more: page < totalPages },
    });
  }),

  http.get("/api/presets/:presetId", async ({ params }) => {
    const preset = db.presets.find((p) => p.id === params.presetId);
    if (!preset) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(preset);
  }),

  // ── Prompt Templates ───────────────────────────────────────

  http.get("/api/prompt-templates/", async ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") || "12", 10);
    const page = parseInt(url.searchParams.get("page") || "1", 10);

    await delay(150);

    const items = [...db.promptTemplates];
    const total = items.length;
    const totalPages = Math.ceil(total / limit);
    const start = (page - 1) * limit;
    const paged = items.slice(start, start + limit);

    return HttpResponse.json({
      items: paged,
      meta: { total, page, limit, has_more: page < totalPages },
    });
  }),

  http.get("/api/prompt-templates/:templateId", async ({ params }) => {
    const tpl = db.promptTemplates.find((t) => t.id === params.templateId);
    if (!tpl) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(tpl);
  }),

  // ── Prompt Fragments ───────────────────────────────────────

  http.get("/api/prompt-fragments/", async ({ request }) => {
    const url = new URL(request.url);
    const fragmentType = url.searchParams.get("fragment_type");
    const isGlobal = url.searchParams.get("is_global");

    await delay(150);

    let items = [...db.promptFragments];
    if (fragmentType) {
      items = items.filter((f) => f.fragment_type === fragmentType);
    }
    if (isGlobal !== null && isGlobal !== undefined && isGlobal !== "") {
      items = items.filter((f) => f.is_global === (isGlobal === "true"));
    }

    return HttpResponse.json(items);
  }),

  http.get("/api/prompt-fragments/:fragmentId", async ({ params }) => {
    const fragment = db.promptFragments.find((f) => f.id === params.fragmentId);
    if (!fragment) return new HttpResponse(null, { status: 404 });
    await delay(100);
    return HttpResponse.json(fragment);
  }),

  // ── Lorebooks ─────────────────────────────────────────────

  http.get("/api/lorebooks", async ({ request }) => {
    const url = new URL(request.url);
    const characterId = url.searchParams.get("character_id");
    const isGlobal = url.searchParams.get("is_global");

    await delay(150);

    let items = [...db.lorebooks];
    if (characterId) {
      items = items.filter((l) => l.character_id === characterId);
    }
    if (isGlobal !== null && isGlobal !== undefined && isGlobal !== "") {
      items = items.filter((l) => l.is_global === (isGlobal === "true"));
    }

    // Return without entries for list endpoint
    const stripped = items.map(({ entries: _entries, ...rest }) => rest);
    return HttpResponse.json(stripped);
  }),

  http.post("/api/lorebooks", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["LorebookCreate"];
    await delay(200);

    const newLorebook: LorebookDetail = {
      id: `lorebook-${Date.now()}`,
      name: body.name,
      description: body.description ?? null,
      is_global: body.is_global ?? false,
      character_id: body.character_id ?? null,
      entries: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    db.lorebooks.unshift(newLorebook);
    const { entries: _entries, ...response } = newLorebook;
    return HttpResponse.json(response, { status: 201 });
  }),

  http.get("/api/lorebooks/:lorebookId", async ({ params }) => {
    const lorebook = db.lorebooks.find((l) => l.id === params.lorebookId);
    if (!lorebook) return new HttpResponse(null, { status: 404 });
    await delay(150);
    return HttpResponse.json(lorebook);
  }),

  http.put("/api/lorebooks/:lorebookId", async ({ params, request }) => {
    const lorebook = db.lorebooks.find((l) => l.id === params.lorebookId);
    if (!lorebook) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as components["schemas"]["LorebookUpdate"];

    if (body.name !== undefined && body.name !== null) lorebook.name = body.name;
    if (body.description !== undefined) lorebook.description = body.description ?? null;
    if (body.is_global !== undefined && body.is_global !== null) lorebook.is_global = body.is_global;
    lorebook.updated_at = new Date().toISOString();

    await delay(200);
    const { entries: _entries, ...response } = lorebook;
    return HttpResponse.json(response);
  }),

  http.delete("/api/lorebooks/:lorebookId", async ({ params }) => {
    const idx = db.lorebooks.findIndex((l) => l.id === params.lorebookId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.lorebooks.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/lorebooks/:lorebookId/entries", async ({ params, request }) => {
    const lorebook = db.lorebooks.find((l) => l.id === params.lorebookId);
    if (!lorebook) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as components["schemas"]["LoreEntryCreate"];
    await delay(200);

    const newEntry: LoreEntryResponse = {
      id: `lore-entry-${Date.now()}`,
      lorebook_id: params.lorebookId as string,
      name: body.name,
      content: body.content,
      keys: body.keys ?? [],
      secondary_keys: body.secondary_keys ?? [],
      secondary_logic: body.secondary_logic ?? "and_any",
      case_sensitive: body.case_sensitive ?? false,
      match_whole_words: body.match_whole_words ?? false,
      use_regex: body.use_regex ?? false,
      enabled: body.enabled ?? true,
      constant: body.constant ?? false,
      position: body.position ?? "after_character",
      depth: body.depth ?? 4,
      role: body.role ?? "system",
      priority: body.priority ?? 100,
      scan_depth: body.scan_depth ?? null,
      ignore_budget: body.ignore_budget ?? false,
      order: body.order ?? 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    lorebook.entries.push(newEntry);
    return HttpResponse.json(newEntry, { status: 201 });
  }),

  http.put("/api/lorebooks/:lorebookId/entries/:entryId", async ({ params, request }) => {
    const lorebook = db.lorebooks.find((l) => l.id === params.lorebookId);
    if (!lorebook) return new HttpResponse(null, { status: 404 });
    const entry = lorebook.entries.find((e) => e.id === params.entryId);
    if (!entry) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as components["schemas"]["LoreEntryUpdate"];

    if (body.name !== undefined && body.name !== null) entry.name = body.name;
    if (body.content !== undefined && body.content !== null) entry.content = body.content;
    if (body.keys !== undefined && body.keys !== null) entry.keys = body.keys;
    if (body.secondary_keys !== undefined && body.secondary_keys !== null) entry.secondary_keys = body.secondary_keys;
    if (body.secondary_logic !== undefined && body.secondary_logic !== null) entry.secondary_logic = body.secondary_logic;
    if (body.case_sensitive !== undefined && body.case_sensitive !== null) entry.case_sensitive = body.case_sensitive;
    if (body.match_whole_words !== undefined && body.match_whole_words !== null) entry.match_whole_words = body.match_whole_words;
    if (body.use_regex !== undefined && body.use_regex !== null) entry.use_regex = body.use_regex;
    if (body.enabled !== undefined && body.enabled !== null) entry.enabled = body.enabled;
    if (body.constant !== undefined && body.constant !== null) entry.constant = body.constant;
    if (body.position !== undefined && body.position !== null) entry.position = body.position;
    if (body.depth !== undefined && body.depth !== null) entry.depth = body.depth;
    if (body.role !== undefined && body.role !== null) entry.role = body.role;
    if (body.priority !== undefined && body.priority !== null) entry.priority = body.priority;
    if (body.scan_depth !== undefined) entry.scan_depth = body.scan_depth ?? null;
    if (body.ignore_budget !== undefined && body.ignore_budget !== null) entry.ignore_budget = body.ignore_budget;
    if (body.order !== undefined && body.order !== null) entry.order = body.order;
    entry.updated_at = new Date().toISOString();

    await delay(200);
    return HttpResponse.json(entry);
  }),

  http.delete("/api/lorebooks/:lorebookId/entries/:entryId", async ({ params }) => {
    const lorebook = db.lorebooks.find((l) => l.id === params.lorebookId);
    if (!lorebook) return new HttpResponse(null, { status: 404 });
    const idx = lorebook.entries.findIndex((e) => e.id === params.entryId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    lorebook.entries.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // ── RAG Search ────────────────────────────────────────────

  http.post("/api/rag/search", async ({ request }) => {
    const body = (await request.json()) as components["schemas"]["RAGSearchRequest"];
    await delay(300);

    const mockResults: components["schemas"]["RetrievedChunk"][] = [
      {
        content: `The Tribunal, also known as ALMSIVI, achieved divinity through the Heart of Lorkhan. This knowledge is central to understanding Morrowind's political and religious landscape. Query matched: "${body.query}"`,
        score: 0.92,
        source_type: "data_bank",
        source_id: "db-entry-1",
        chunk_index: 0,
      },
      {
        content: `Red Mountain eruptions have shaped the geography and culture of Vvardenfell for millennia. The Blight emanating from its depths is a constant threat to all inhabitants. Related to: "${body.query}"`,
        score: 0.78,
        source_type: "lorebook",
        source_id: "lorebook-1",
        chunk_index: 1,
      },
      {
        content: `Aranwen's banishment from the Clockwork City was precipitated by her questioning of the Tribunal's manufactured divinity, a heresy within the Dunmer faith. Context: "${body.query}"`,
        score: 0.65,
        source_type: "character",
        source_id: "7384-aranwen-the-banished",
        chunk_index: 0,
      },
    ];

    const maxResults = body.max_results ?? 5;
    return HttpResponse.json(mockResults.slice(0, maxResults));
  }),

  http.get("/api/rag/status", async () => {
    await delay(100);
    return HttpResponse.json({
      status: "active",
      indexed_count: 150,
      last_indexed: new Date().toISOString(),
      embedding_provider: "mock-embeddings",
    });
  }),

  // ── Character Import ──────────────────────────────────────

  http.post("/api/characters/import", async ({ request }) => {
    await delay(400);
    const formData = await request.formData();
    const file = formData.get("file");

    const fileName = file instanceof File ? file.name : "imported-character";
    const baseName = fileName.replace(/\.(json|png)$/i, "");
    const slugName = baseName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");

    const newChar: Character = {
      id: `${Date.now()}-${slugName}`,
      name: baseName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      description: `An imported character from ${fileName}. This character was brought into the library via file import.`,
      personality: "Mysterious and intriguing, with a backstory yet to be fully explored.",
      first_message: `*looks up from an ancient tome* Greetings, traveler. I am newly arrived in this realm, imported from distant lands. What would you know of me?`,
      example_dialogues: [],
      scenario: null,
      post_history_instructions: null,
      alternate_greetings: null,
      tags: ["Imported"],
      gender: null,
      custom_gender: null,
      creator: "Import",
      version: 1,
      avatar: null,
      avatar_thumbnail: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    db.characters.unshift(newChar);
    return HttpResponse.json(newChar, { status: 201 });
  }),

  // ── Persona CRUD ──────────────────────────────────────────

  http.post("/api/personas/", async ({ request }) => {
    await delay(200);
    const formData = await request.formData();

    const name = formData.get("name") as string;
    if (!name) {
      return HttpResponse.json({ detail: "name is required" }, { status: 422 });
    }

    const newPersona: Persona = {
      id: `persona-${Date.now()}`,
      name,
      description: (formData.get("description") as string) || null,
      is_default: formData.get("is_default") === "true",
      avatar: (formData.get("avatar") as string) || null,
      avatar_thumbnail: (formData.get("avatar") as string) || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // If setting as default, unset others
    if (newPersona.is_default) {
      db.personas.forEach((p) => (p.is_default = false));
    }

    db.personas.unshift(newPersona);
    return HttpResponse.json(newPersona, { status: 201 });
  }),

  http.put("/api/personas/:personaId", async ({ params, request }) => {
    const persona = db.personas.find((p) => p.id === params.personaId);
    if (!persona) return new HttpResponse(null, { status: 404 });

    await delay(200);
    const formData = await request.formData();

    const name = formData.get("name") as string | null;
    if (name !== null) persona.name = name;

    const desc = formData.get("description") as string | null;
    if (desc !== null) persona.description = desc || null;

    const isDefault = formData.get("is_default");
    if (isDefault !== null) {
      const newDefault = isDefault === "true";
      if (newDefault && !persona.is_default) {
        db.personas.forEach((p) => (p.is_default = false));
      }
      persona.is_default = newDefault;
    }

    const avatar = formData.get("avatar") as string | null;
    if (avatar !== null) {
      persona.avatar = avatar || null;
      persona.avatar_thumbnail = avatar || null;
    }

    persona.updated_at = new Date().toISOString();
    return HttpResponse.json(persona);
  }),

  http.delete("/api/personas/:personaId", async ({ params }) => {
    const idx = db.personas.findIndex((p) => p.id === params.personaId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.personas.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/personas/:personaId/set-default", async ({ params }) => {
    const persona = db.personas.find((p) => p.id === params.personaId);
    if (!persona) return new HttpResponse(null, { status: 404 });

    db.personas.forEach((p) => (p.is_default = false));
    persona.is_default = true;
    persona.updated_at = new Date().toISOString();

    await delay(150);
    return HttpResponse.json(persona);
  }),

  // ── Prompt Template CRUD (detail) ─────────────────────────

  http.put("/api/prompt-templates/:templateId", async ({ params, request }) => {
    const tpl = db.promptTemplates.find((t) => t.id === params.templateId);
    if (!tpl) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    for (const key of [
      "name",
      "description",
      "is_default",
      "system_template",
      "component_order",
      "components_enabled",
      "max_history_tokens",
    ]) {
      if (body[key] !== undefined) (tpl as any)[key] = body[key];
    }
    tpl.updated_at = new Date().toISOString();
    await delay(200);
    return HttpResponse.json(tpl);
  }),

  http.delete("/api/prompt-templates/:templateId", async ({ params }) => {
    const idx = db.promptTemplates.findIndex((t) => t.id === params.templateId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.promptTemplates.splice(idx, 1);
    db.templateFragments.delete(params.templateId as string);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/prompt-templates/:templateId/preview", async ({ params, request }) => {
    const tpl = db.promptTemplates.find((t) => t.id === params.templateId);
    if (!tpl) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    await delay(300);

    // Build a mock rendered string using the sample data
    const rendered = `You are ${body.character_name || "Alice"}, a ${body.character_description || "helpful AI assistant"}. You are ${body.character_personality || "Friendly and knowledgeable"}. Scenario: ${body.character_scenario || "Casual conversation"}. [User: ${body.persona_name || "User"} - ${body.persona_description || "A curious person"}]`;

    return HttpResponse.json({
      rendered,
      variables_used: {
        character_name: body.character_name || "Alice",
        character_description: body.character_description || "A helpful AI assistant",
        character_personality: body.character_personality || "Friendly and knowledgeable",
        character_scenario: body.character_scenario || "Casual conversation",
        persona_name: body.persona_name || "User",
        persona_description: body.persona_description || "A curious person",
      },
    });
  }),

  // ── Template Fragments (associations) ─────────────────────

  http.get("/api/prompt-templates/:templateId/fragments/", async ({ params }) => {
    const templateId = params.templateId as string;
    const tpl = db.promptTemplates.find((t) => t.id === templateId);
    if (!tpl) return new HttpResponse(null, { status: 404 });
    await delay(100);
    const frags = db.templateFragments.get(templateId) || [];
    return HttpResponse.json(frags);
  }),

  http.post("/api/prompt-templates/:templateId/fragments/", async ({ params, request }) => {
    const templateId = params.templateId as string;
    const tpl = db.promptTemplates.find((t) => t.id === templateId);
    if (!tpl) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    const fragment = db.promptFragments.find((f) => f.id === body.fragment_id);
    if (!fragment) return new HttpResponse(null, { status: 404 });

    const newTf: TemplateFragmentResponse = {
      id: `tf-${Date.now()}`,
      template_id: templateId,
      fragment_id: body.fragment_id,
      position: body.position || "after_system",
      ordinal: body.ordinal ?? 0,
      created_at: new Date().toISOString(),
      fragment,
    };

    if (!db.templateFragments.has(templateId)) {
      db.templateFragments.set(templateId, []);
    }
    db.templateFragments.get(templateId)!.push(newTf);
    await delay(200);
    return HttpResponse.json(newTf, { status: 201 });
  }),

  http.delete("/api/prompt-templates/:templateId/fragments/:fragmentId", async ({ params }) => {
    const templateId = params.templateId as string;
    const fragmentId = params.fragmentId as string;
    const frags = db.templateFragments.get(templateId);
    if (!frags) return new HttpResponse(null, { status: 404 });
    const idx = frags.findIndex((f) => f.fragment_id === fragmentId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    frags.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Prompt Fragment CRUD (detail) ─────────────────────────

  http.put("/api/prompt-fragments/:fragmentId", async ({ params, request }) => {
    const fragment = db.promptFragments.find((f) => f.id === params.fragmentId);
    if (!fragment) return new HttpResponse(null, { status: 404 });
    const body = (await request.json()) as any;
    for (const key of ["name", "description", "fragment_type", "content", "is_global"]) {
      if (body[key] !== undefined) (fragment as any)[key] = body[key];
    }
    fragment.updated_at = new Date().toISOString();
    await delay(200);
    return HttpResponse.json(fragment);
  }),

  http.delete("/api/prompt-fragments/:fragmentId", async ({ params }) => {
    const idx = db.promptFragments.findIndex((f) => f.id === params.fragmentId);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    db.promptFragments.splice(idx, 1);
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),
];
