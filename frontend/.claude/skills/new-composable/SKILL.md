---
name: new-composable
description: Scaffold a feature-scoped Vue composable (use* prefix) following the project's View -> Component -> Composable -> API layering, with the typed openapi-fetch client and { data, error } handling. Use when adding data fetching or shared feature state.
---

Create a composable that owns a feature's data fetching and reactive state — the layer components delegate to instead of calling the API directly.

## Conventions

- File `src/composables/use<Thing>.ts`, camelCase, `use*` prefix. Returns reactive `ref`/`computed` + action functions — never a raw `Response`.
- Call the **typed client**: `import { client } from "@/api/client"` then `const { data, error } = await client.GET("/api/...", { params: { query: {...} } })`. Branch on `error` before using `data`. Type with `components["schemas"][...]` from `@/api/schema`.
- FormData / multipart mutations (file uploads) are the one sanctioned `fetch()` exception — openapi-fetch doesn't handle multipart.
- Surface user-facing errors via `useAppToast`; don't swallow them.
- Singletons that outlive a feature (theme, sidebar) share one module-level ref and persist to `localStorage`; truly global app state goes in a Pinia store under `src/stores/`.

## Shape

```ts
import { ref } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type Thing = components["schemas"]["ThingResponse"];

export function useThings() {
  const items = ref<Thing[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function load() {
    loading.value = true;
    error.value = null;
    const { data, error: err } = await client.GET("/api/things");
    if (err) error.value = "Failed to load things";
    else items.value = data?.items ?? [];
    loading.value = false;
  }

  return { items, loading, error, load };
}
```

## Finish

`bun run typecheck`. Wire the composable into a component/view — never fetch in the template.
