import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { useListCrud } from "@/composables/useListCrud";

export type DataBankEntry = components["schemas"]["DataBankResponse"];
export type DataBankCreate = components["schemas"]["DataBankCreate"];
export type DataBankUpdate = components["schemas"]["DataBankUpdate"];

export function useDataBank(options: { autoLoad?: boolean } = {}) {
  const { items, loading, error, fetchList, refresh, createItem, updateItem, removeItem } =
    useListCrud<
      DataBankEntry,
      [scope?: string, chatId?: string, characterId?: string],
      DataBankCreate,
      DataBankUpdate
    >({
      label: "entry",
      labelPlural: "data bank entries",
      autoLoad: options.autoLoad ?? true,
      list: (scope, chatId, characterId) => {
        const query: { scope?: string; chat_id?: string; character_id?: string } = {};
        if (scope) query.scope = scope;
        if (chatId) query.chat_id = chatId;
        if (characterId) query.character_id = characterId;
        return client.GET("/api/data-bank/", { params: { query } });
      },
      create: (body) => client.POST("/api/data-bank/", { body }),
      update: (id, body) =>
        client.PUT("/api/data-bank/{entry_id}", { params: { path: { entry_id: id } }, body }),
      remove: (id) =>
        client.DELETE("/api/data-bank/{entry_id}", { params: { path: { entry_id: id } } }),
    });

  return {
    entries: items,
    loading,
    error,
    fetchEntries: fetchList,
    createEntry: createItem,
    updateEntry: updateItem,
    deleteEntry: removeItem,
    refresh,
  };
}
