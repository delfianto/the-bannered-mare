import type { components } from "@/api/schema";

/** Character type from API */
export type Character = components["schemas"]["CharacterResponse"];

export type ViewMode = "grid" | "list";
export type SortOption = "recent" | "name-asc" | "name-desc" | "newest";

export interface FilterState {
  search: string;
  category: string;
  sort: SortOption;
  viewMode: ViewMode;
}
