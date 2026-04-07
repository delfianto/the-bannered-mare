import { http, HttpResponse, delay } from "msw";
import { characters } from "@/mocks/data/characters";
import { chats } from "@/mocks/data/chats";
import { providers } from "@/mocks/data/providers";
import { modelsPages, modelsFilteredByName } from "@/mocks/data/models";
import { allModelsMock } from "@/mocks/data/models-data";
import { personas } from "@/mocks/data/personas";
import { modelFamiliesPages, modelFamiliesFilteredByName } from "@/mocks/data/model-families";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { modelFamiliesParameterDocs } from "@/mocks/data/model-parameters";
import { conversationCache } from "@/mocks/loader";
import "@/mocks/data/messages"; // Initialize registrations
import type { components } from "@/api/schema";

type Chat = components["schemas"]["ChatResponse"];
type Character = components["schemas"]["CharacterResponse"];

const db = {
  characters,
  chats,
  providers,
  modelsPages,
  allModelsMock,
  personas,
  modelFamiliesPages,
  allModelFamiliesMock,
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

  // Models List
  http.get("/api/models", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const nameParam = url.searchParams.get("name");

    if (nameParam && nameParam.toLowerCase().includes("claude")) {
      return HttpResponse.json(modelsFilteredByName);
    }

    const pageParam = url.searchParams.get("page");
    const page = pageParam ? parseInt(pageParam, 10) : 1;
    const pageData = db.modelsPages.find((p) => p.meta.page === page);
    if (!pageData) return HttpResponse.json(db.modelsPages[0]);
    return HttpResponse.json(pageData);
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

  // Personas
  http.get("/api/personas/", async () => {
    await delay(100);
    return HttpResponse.json(db.personas);
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

    if (nameParam && nameParam.toLowerCase().includes("claude")) {
      return HttpResponse.json(modelFamiliesFilteredByName);
    }

    const pageParam = url.searchParams.get("page");
    const page = pageParam ? parseInt(pageParam, 10) : 1;

    const pageData = db.modelFamiliesPages.find((p) => p.meta.page === page);

    if (!pageData) {
      return HttpResponse.json(db.modelFamiliesPages[0]);
    }

    return HttpResponse.json(pageData);
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
];
