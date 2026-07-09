<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { useModelFamily } from "@/composables/useModelFamily";
import { useAppToast } from "@/composables/useToast";
import type { components } from "@/api/schema";

type ProviderType = components["schemas"]["ProviderType"];

const router = useRouter();
const { createFamily, saving } = useModelFamily();
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
  family_identifier: "",
  description: "",
  provider_types: [] as ProviderType[],
});

const initialSnapshot = JSON.stringify(form);
const saved = ref(false);
const dirty = computed(() => !saved.value && JSON.stringify(form) !== initialSnapshot);

const canCreate = computed(() => !!form.name.trim() && !!form.family_identifier.trim());

function toggleProviderType(t: ProviderType) {
  const i = form.provider_types.indexOf(t);
  if (i === -1) form.provider_types.push(t);
  else form.provider_types.splice(i, 1);
}

async function handleCreate() {
  if (!canCreate.value) {
    toast.error("Name and family identifier are required");
    return;
  }
  try {
    const created = await createFamily({
      name: form.name.trim(),
      family_identifier: form.family_identifier.trim(),
      description: form.description.trim() || null,
      provider_types: form.provider_types,
    });
    saved.value = true; // suppress the unsaved-changes guard on the redirect
    toast.success("Model family created");
    router.push(`/settings/model-families/${created.id}`);
  } catch {
    toast.error("Failed to create model family");
  }
}

function goBack() {
  router.push({ path: "/connections", query: { tab: "model-families" } });
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
          aria-label="Back to model families"
          @click="goBack"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <AppIcon name="i-lucide-layers" class="size-3.5 text-primary-content" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            New Model Family
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
        {{ saving ? "Creating..." : "Create Family" }}
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
                placeholder="e.g. GPT-4 class"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Family identifier -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Family Identifier
              </span>
              <input
                v-model="form.family_identifier"
                type="text"
                placeholder="e.g. gpt-4"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Description -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Description
                <span class="normal-case text-muted-foreground/60">(optional)</span>
              </span>
              <textarea
                v-model="form.description"
                rows="2"
                placeholder="What models belong to this family?"
                class="w-full resize-y rounded-lg border bg-base-300/40 px-4 py-2.5 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Provider types -->
            <div>
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Provider Types
                <span class="normal-case text-muted-foreground/60">(which providers serve it)</span>
              </span>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="pt in providerTypes"
                  :key="pt.value"
                  type="button"
                  class="rounded-full border px-3 py-1 text-xs font-medium transition-colors"
                  :class="
                    form.provider_types.includes(pt.value)
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-base-300 hover:text-foreground'
                  "
                  @click="toggleProviderType(pt.value)"
                >
                  {{ pt.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <p class="px-1 text-[0.6875rem] text-muted-foreground/70">
          Supported inference parameters and defaults can be configured after the family is created.
        </p>
      </div>
    </div>
  </div>
</template>
