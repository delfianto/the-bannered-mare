import { dateMock, idMock } from "./utils";
import type { components } from "@/api/schema";

type Message = components["schemas"]["MessageResponse"];

export interface YamlScenario {
  messages: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
}

/**
 * Lazy conversation cache - only loads when accessed
 */
class ConversationCache {
  private cache: Map<string, Message[]> = new Map();
  private loaders: Map<string, () => Promise<YamlScenario>> = new Map();
  private metadata: Map<string, { daysAgoStart: number; messageCount?: number }> = new Map();

  register(chatId: string, loader: () => Promise<YamlScenario>, daysAgoStart: number = 7) {
    this.loaders.set(chatId, loader);
    this.metadata.set(chatId, { daysAgoStart });
  }

  async get(chatId: string): Promise<Message[] | null> {
    if (this.cache.has(chatId)) {
      return this.cache.get(chatId)!;
    }

    const loader = this.loaders.get(chatId);
    if (!loader) {
      return null;
    }

    const loadedModule = await loader();
    // Handle default export from dynamic import
    const data = "default" in loadedModule ? (loadedModule as any).default : loadedModule;

    const metadata = this.metadata.get(chatId)!;
    const messages = this.hydrate(chatId, data, metadata.daysAgoStart);

    this.cache.set(chatId, messages);
    metadata.messageCount = messages.length;

    return messages;
  }

  /**
   * Get paginated messages (Cursor-based)
   * Returns messages older than the cursor, sorted Newest -> Oldest
   */
  async getCursorPaginated(
    chatId: string,
    limit: number = 20,
    cursor?: string,
  ): Promise<{ messages: Message[]; hasMore: boolean } | null> {
    const allMessages = await this.get(chatId);
    if (!allMessages) {
      return null;
    }

    const sortedMessages = [...allMessages].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    let filteredMessages = sortedMessages;

    if (cursor) {
      const cursorTime = new Date(cursor).getTime();
      filteredMessages = sortedMessages.filter(
        (msg) => new Date(msg.created_at).getTime() < cursorTime,
      );
    }

    const hasMore = filteredMessages.length > limit;

    const messages = filteredMessages.slice(0, limit);

    return { messages, hasMore };
  }

  async getPaginated(
    chatId: string,
    page: number = 1,
    pageSize: number = 50,
  ): Promise<{ messages: Message[]; total: number; hasMore: boolean } | null> {
    const allMessages = await this.get(chatId);
    if (!allMessages) {
      return null;
    }

    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const messages = allMessages.slice(startIndex, endIndex);

    return {
      messages,
      total: allMessages.length,
      hasMore: endIndex < allMessages.length,
    };
  }

  getMessageCount(chatId: string): number | null {
    const metadata = this.metadata.get(chatId);
    return metadata?.messageCount ?? null;
  }

  has(chatId: string): boolean {
    return this.loaders.has(chatId);
  }

  async preload(chatId: string): Promise<void> {
    await this.get(chatId);
  }

  clearCache(chatId?: string): void {
    if (chatId) {
      this.cache.delete(chatId);
      const metadata = this.metadata.get(chatId);
      if (metadata) {
        delete metadata.messageCount;
      }
    } else {
      this.cache.clear();
      this.metadata.forEach((meta) => delete meta.messageCount);
    }
  }

  getStats() {
    return {
      registered: this.loaders.size,
      cached: this.cache.size,
      memoryUsage: Array.from(this.cache.values()).reduce((sum, msgs) => sum + msgs.length, 0),
    };
  }

  /**
   * Hydrate YAML data into Message objects
   */
  private hydrate(chatId: string, data: YamlScenario, daysAgoStart: number): Message[] {
    const timestamps = dateMock.chatMessageTimestamps(daysAgoStart, data.messages.length);

    return data.messages.map((msg, index) => ({
      id: idMock.generateMessageId(chatId, index),
      chat_id: chatId,
      role: msg.role,
      content: msg.content.trim(),
      active_index: 0,
      created_at: timestamps[index],
    }));
  }
}

export const conversationCache = new ConversationCache();

/**
 * Legacy compatibility function
 */
export function loadConversation(
  chatId: string,
  data: YamlScenario,
  daysAgoStart: number = 7,
): Message[] {
  const timestamps = dateMock.chatMessageTimestamps(daysAgoStart, data.messages.length);

  return data.messages.map((msg, index) => ({
    id: idMock.generateMessageId(chatId, index),
    chat_id: chatId,
    role: msg.role,
    content: msg.content.trim(),
    active_index: 0,
    created_at: timestamps[index],
  }));
}
