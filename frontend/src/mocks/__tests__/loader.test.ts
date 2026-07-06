import { describe, it, expect, beforeEach } from "bun:test";
import { conversationCache } from "../loader";

describe("ConversationCache", () => {
  beforeEach(() => {
    conversationCache.clearCache();
  });

  it("should register and load conversations", async () => {
    conversationCache.register(
      "test-chat",
      async () => ({
        messages: [
          { role: "user", content: "Hello" },
          { role: "assistant", content: "Hi there!" },
        ],
      }),
      7,
    );

    const messages = await conversationCache.get("test-chat");
    expect(messages).not.toBeNull();
    expect(messages!.length).toBe(2);
    expect(messages![0].role).toBe("user");
    // Hydrated messages should have generated IDs and timestamps
    expect(messages![0].id).toBeDefined();
    expect(messages![0].created_at).toBeDefined();
  });

  it("should paginate with cursor", async () => {
    // create 5 messages
    const mockMessages = [
      { role: "user", content: "Msg 1" },
      { role: "assistant", content: "Msg 2" },
      { role: "user", content: "Msg 3" },
      { role: "assistant", content: "Msg 4" },
      { role: "user", content: "Msg 5" },
    ] as const;

    conversationCache.register("chat-pagination", async () => ({ messages: [...mockMessages] }), 1);

    // 1. Initial Load (Limit 2) -> Should get Msg 5, Msg 4 (Newest first)
    // getCursorPaginated sorts Newest -> Oldest
    const page1 = await conversationCache.getCursorPaginated("chat-pagination", 2);
    expect(page1).not.toBeNull();
    expect(page1!.messages.length).toBe(2);
    expect(page1!.hasMore).toBe(true);

    // Msg 5 is the newest (last in the original array which simulates time passing)
    // loader.ts hydrate maps index 0 to oldest, index N to newest.
    // So Msg 5 (index 4) is newest.
    expect(page1!.messages[0].content).toBe("Msg 5");
    expect(page1!.messages[1].content).toBe("Msg 4");

    // 2. Next Page (Limit 2, Cursor = Msg 4's created_at)
    // Should get Msg 3, Msg 2
    const cursor = page1!.messages[1].created_at;
    const page2 = await conversationCache.getCursorPaginated("chat-pagination", 2, cursor);

    expect(page2).not.toBeNull();
    expect(page2!.messages.length).toBe(2);
    expect(page2!.hasMore).toBe(true);
    expect(page2!.messages[0].content).toBe("Msg 3");
    expect(page2!.messages[1].content).toBe("Msg 2");

    // 3. Last Page
    const cursor2 = page2!.messages[1].created_at;
    const page3 = await conversationCache.getCursorPaginated("chat-pagination", 2, cursor2);

    expect(page3).not.toBeNull();
    expect(page3!.messages.length).toBe(1);
    expect(page3!.hasMore).toBe(false);
    expect(page3!.messages[0].content).toBe("Msg 1");

    // 4. Empty Page
    const cursor3 = page3!.messages[0].created_at;
    const page4 = await conversationCache.getCursorPaginated("chat-pagination", 2, cursor3);

    expect(page4).not.toBeNull();
    expect(page4!.messages.length).toBe(0);
    expect(page4!.hasMore).toBe(false);
  });
});
