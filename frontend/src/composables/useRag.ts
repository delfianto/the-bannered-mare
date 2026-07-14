import { client, extractApiError } from "@/api/client";
import type { components } from "@/api/schema";

export type RetrievedChunk = components["schemas"]["RetrievedChunk"];

/**
 * RAG semantic search. Keeps the call out of the view (MemoryView was speaking
 * HTTP directly) and gives search real error handling instead of swallowing
 * failures into an empty result set.
 */
export function useRag() {
  async function search(query: string, maxResults = 5, threshold = 0.3): Promise<RetrievedChunk[]> {
    const { data, error, response } = await client.POST("/api/rag/search", {
      body: { query, max_results: maxResults, threshold },
    });
    if (error) throw extractApiError(error, "Search failed", response?.status);
    return data ?? [];
  }

  return { search };
}
