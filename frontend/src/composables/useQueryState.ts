import { useRoute, useRouter } from "vue-router";

/**
 * Persist list UI state (search, filters, page) in the URL query so it survives
 * navigating into a detail view and back — the same `?tab=` idiom ConnectionsView
 * already uses. Without this, a filtered table remounts on browser-back and
 * resets to page 1 with no filters.
 *
 * `patchQuery` merges into the *current* query (so unrelated keys like `tab` are
 * preserved), drops keys whose value is `undefined`/empty (keeping URLs clean),
 * and uses `replace` so filter tweaks don't pile up in the history stack.
 */
export function useQueryState() {
  const route = useRoute();
  const router = useRouter();

  function readQuery(key: string): string | undefined {
    const v = route.query[key];
    return typeof v === "string" && v !== "" ? v : undefined;
  }

  function patchQuery(patch: Record<string, string | number | undefined>) {
    const next: Record<string, string> = {};
    for (const [k, v] of Object.entries(route.query)) {
      if (typeof v === "string") next[k] = v;
    }
    for (const [k, v] of Object.entries(patch)) {
      if (v === undefined || v === "") delete next[k];
      else next[k] = String(v);
    }
    void router.replace({ query: next });
  }

  return { readQuery, patchQuery };
}
