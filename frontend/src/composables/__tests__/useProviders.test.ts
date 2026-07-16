import { defineComponent, h } from "vue";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useProviders, type Provider } from "@/composables/useProviders";

// Proves the msw/node seam. Drives the real `useProviders` composable
// (→ settings store → typed openapi-fetch client → UNPATCHED fetch) and asserts
// it loads the `/api/providers` fixture through the shared MSW handler set, with
// no `global.fetch`/`client` monkeypatch. `VITE_API_URL` is "" in tests, so the
// client issues the relative `/api/providers` path; happy-dom resolves it against
// its default origin and msw/node matches the handler by pathname.
describe("useProviders (msw/node seam)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("loads the provider fixture via the real MSW handler", async () => {
    // A throwaway host component so the composable's onMounted fetch fires under
    // a real lifecycle — no faked fetch, no manual client call.
    let api!: ReturnType<typeof useProviders>;
    mount(
      defineComponent({
        setup() {
          api = useProviders();
          return () => h("div");
        },
      }),
    );

    await vi.waitFor(() => expect(api.providers.value.length).toBeGreaterThan(0));

    expect(api.error.value).toBeNull();
    const providers: Provider[] = api.providers.value;
    const openai = providers.find((p) => p.id === "prov-openai");
    expect(openai?.name).toBe("OpenAI");
    expect(openai?.provider_type).toBe("openai");
  });
});
