export interface LibraryCharacter {
  id: string;
  name: string;
  title: string;
  imageUrl: string;
  tags: string[];
  species: string;
  gender: string;
  description: string;
  chatCount: number;
  creator: string;
  source: "created" | "imported";
  lastUsed: string;
  sessionCount: number;
  createdAt: string;
}

export type ViewMode = "grid" | "list";
export type SortOption = "recent" | "name-asc" | "name-desc" | "sessions" | "newest";
export type SourceFilter = "all" | "created" | "imported";

export interface FilterState {
  search: string;
  category: string;
  source: SourceFilter;
  sort: SortOption;
  viewMode: ViewMode;
}
