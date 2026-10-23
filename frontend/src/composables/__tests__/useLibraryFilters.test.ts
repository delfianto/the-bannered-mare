import { describe, expect, it } from "vite-plus/test";
import { ref } from "vue";
import { useLibraryFilters } from "@/composables/useLibraryFilters";
import type { Character } from "@/types/discover";
import { characters } from "@/mocks/data/characters";
const source = () =>
  ref<Character[]>([
    {
      ...characters[0],
      id: "a",
      name: "Zara",
      tags: ["Fantasy"],
      gender: "female",
      description: "A dragon rider",
      created_at: "2026-01-01T00:00:00Z",
    },
    {
      ...characters[1],
      id: "b",
      name: "Aran",
      tags: ["Scholar"],
      gender: null,
      description: null,
      created_at: "2026-10-01T00:00:00Z",
    },
    {
      ...characters[2],
      id: "c",
      name: "Mira",
      tags: null,
      gender: "female",
      description: "An astronomer",
      created_at: "2026-05-01T00:00:00Z",
    },
  ]);

describe("character library filters", () => {
  it.each([
    ["ZARA", ["a"]],
    ["dragon", ["a"]],
    ["scholar", ["b"]],
    ["female", ["a", "c"]],
    ["missing", []],
  ])("searches name, description, tags and gender: %s", (query, ids) => {
    const api = useLibraryFilters(source());
    api.setSearch(query);
    expect(api.filtered.value.map((c) => c.id)).toEqual(ids);
  });

  it("combines search and case-insensitive category filters and preserves source order", () => {
    const rows = source();
    const api = useLibraryFilters(rows);
    api.setSearch("a");
    api.setCategory("FANTASY");
    expect(api.filtered.value.map((c) => c.id)).toEqual(["a"]);
    api.setCategory("All");
    expect(api.filtered.value.map((c) => c.id)).toEqual(["a", "b", "c"]);
    expect(rows.value.map((c) => c.id)).toEqual(["a", "b", "c"]);
  });

  it.each([
    ["name-asc", ["b", "c", "a"]],
    ["name-desc", ["a", "c", "b"]],
    ["newest", ["b", "c", "a"]],
    ["recent", ["a", "b", "c"]],
  ] as const)("sorts %s without mutating shared data", (sort, expected) => {
    const rows = source();
    const api = useLibraryFilters(rows, { sort });
    expect(api.filtered.value.map((c) => c.id)).toEqual(expected);
    expect(rows.value[0].id).toBe("a");
    api.setSort("recent");
    expect(api.filtered.value[0].id).toBe("a");
  });

  it("reacts to newly fetched characters and keeps restored UI state", () => {
    const rows = source();
    const api = useLibraryFilters(rows, { search: "Aran", viewMode: "list" });
    expect(api.filters.viewMode).toBe("list");
    rows.value = [];
    expect(api.filtered.value).toEqual([]);
    api.setViewMode("grid");
    expect(api.filters.viewMode).toBe("grid");
  });
});
