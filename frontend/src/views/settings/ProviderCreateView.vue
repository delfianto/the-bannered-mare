<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { useProvider } from "@/composables/useProvider";
import { useAppToast } from "@/composables/useToast";
import type { components } from "@/api/schema";

type ProviderType = components["schemas"]["ProviderType"];

const router = useRouter();
const { createProvider, saving } = useProvider();
const toast = useAppToast();

const providerTypes: { value: ProviderType; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "xai", label: "xAI" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama" },
  { value: "lmstudio", label: "LM Studio" },
  { value: "custom", label: "Custom" },
];

const form = reactive({
  name: "",
  provider_type: "" as ProviderType | "",
  base_url: "",
  api_key_env_var: "",
});

const initialSnapshot = JSON.stringify(form);
const saved = ref(false);
const dirty = computed(() => !saved.value && JSON.stringify(form) !== initialSnapshot);

const isCustom = computed(() => form.provider_type === "custom");
const typeName = computed(
  () => providerTypes.find((t) => t.value === form.provider_type)?.label || "Select a type",
);

// Custom providers must declare both a base URL and an API-key env var; other
// provider types must NOT set an env var (the backend rejects it).
const canCreate = computed(
  () =>
    !!form.name.trim() &&
    !!form.provider_type &&
    (!isCustom.value || (!!form.base_url.trim() && !!form.api_key_env_var.trim())),
);

async function handleCreate() {
  if (!canCreate.value || !form.provider_type) {
    toast.error("Name and type are required (custom providers also need a base URL and key env var)");
    return;
  }
  try {
    const created = await createProvider({
      name: form.name.trim(),
      provider_type: form.provider_type,
      base_url: form.base_url.trim() || null,
      api_key_env_var: isCustom.value ? form.api_key_env_var.trim() : null,
    });
    saved.value = true; // suppress the unsaved-changes guard on the redirect
    toast.success("Provider created");
    router.push(`/settings/providers/${created.id}`);
  } catch {
    toast.error("Failed to create provider");
  }
}

function goBack() {
  router.push({ path: "/connections", query: { tab: "providers" } });
}

// --- Unsaved-changes guards ---
function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
onMounted(() => window.addEventListener("beforeunload", beforeUnloadHandler));
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnloadHandler));

onBeforeRouteLeave(() => {
  if (dirty.value) {
    return window.confirm("You have unsaved changes. Leave and discard them?");
  }
  return true;
});
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header
      class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
    >
      <div class="flex items-center gap-3">
        <button
          class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          aria-label="Back to providers"
          @click="goBack"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <AppIcon name="i-lucide-plug" class="size-3.5 text-primary-content" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            New Provider
          </h1>
        </div>
      </div>

      <button
        class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96] disabled:pointer-events-none disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="handleCreate"
      >
        <AppIcon
          :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
          class="size-4"
          :class="{ 'animate-spin': saving }"
        />
        {{ saving ? "Creating..." : "Create Provider" }}
      </button>
    </header>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-2xl space-y-6">
        <div class="rounded-xl border bg-base-200/50 p-5">
          <h2
            class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
          >
            Identity
          </h2>
          <div class="space-y-4">
            <!-- Name -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Name
              </span>
              <input
                v-model="form.name"
                type="text"
                placeholder="Provider name"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Provider type -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Provider Type
              </span>
              <SelectMenu
                v-model="form.provider_type"
                :items="providerTypes"
                value-key="value"
                :search-input="false"
                class="w-full"
              >
                <button
                  class="flex h-11 w-full items-center rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30"
                >
                  {{ typeName }}
                </button>
              </SelectMenu>
            </label>

            <!-- Base URL -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Base URL
                <span v-if="isCustom" class="text-error">*</span>
                <span v-else class="normal-case text-muted-foreground/60">(optional)</span>
              </span>
              <input
                v-model="form.base_url"
                type="text"
                placeholder="https://api.example.com/v1"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
              <span class="mt-1 block text-[0.625rem] text-muted-foreground/70">
                Known providers use a sensible default when left blank.
              </span>
            </label>

            <!-- API key env var (custom only) -->
            <label v-if="isCustom" class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                API Key Env Var <span class="text-error">*</span>
              </span>
              <input
                v-model="form.api_key_env_var"
                type="text"
                placeholder="E.G. MY_PROVIDER_API_KEY"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
              <span class="mt-1 block text-[0.625rem] text-muted-foreground/70">
                The environment variable the server reads the API key from.
              </span>
            </label>
          </div>
        </div>

        <p class="px-1 text-[0.6875rem] text-muted-foreground/70">
          After creating, you can sync the provider's models and curate its allow-list from the
          provider page.
        </p>
      </div>
    </div>
  </div>
</template>
