<script setup lang="ts">
import { reactive, ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { useModel } from "@/composables/useModel";
import { useProviders } from "@/composables/useProviders";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { useAppToast } from "@/composables/useToast";
import { providersForFamily } from "@/utils/modelProviderFilter";

const route = useRoute();
const router = useRouter();
const { createModel, saving } = useModel();
const { providers } = useProviders();
const { families } = useModelFamilies({ pageSize: 100 });
const toast = useAppToast();

// Prefilled from the provider's "Add as Model" action (or blank for a fresh one).
const form = reactive({
  name: (route.query.name as string) || "",
  model_identifier: (route.query.model_identifier as string) || "",
  provider_id: (route.query.provider_id as string) || "",
  model_family_id: "",
  use_openrouter: false,
  openrouter_identifier: "",
  enabled: true,
});

const initialSnapshot = JSON.stringify(form);
const saved = ref(false);
const dirty = computed(() => !saved.value && JSON.stringify(form) !== initialSnapshot);

const selectUi = {
  base: "w-full border-none shadow-none ring-0 outline-none p-0 bg-transparent",
  content: "w-[var(--reka-popper-anchor-width)] border bg-card ring-0 outline-none shadow-lg",
  item: "text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent",
};

const selectedFamily = computed(() =>
  families.value.find((f: any) => f.id === form.model_family_id),
);
const providerItems = computed(() =>
  providersForFamily(providers.value as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...families.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);
// Fall back to the full provider list so a prefilled provider still displays
// before its family is chosen.
const providerName = computed(
  () => providers.value.find((p: any) => p.id === form.provider_id)?.name || "Select a provider",
);
const familyName = computed(
  () => familyItems.value.find((i) => i.value === form.model_family_id)?.label || "Select a family",
);
// A model is available on OpenRouter iff it has an OpenRouter identifier.
const canUseOpenrouter = computed(() => !!form.openrouter_identifier.trim());

function toggleUseOpenrouter() {
  if (!canUseOpenrouter.value) return;
  form.use_openrouter = !form.use_openrouter;
}

watch(
  () => form.openrouter_identifier,
  (v) => {
    if (!v.trim()) form.use_openrouter = false;
  },
);

// Provider is constrained by the family. On family change, drop an incompatible
// provider; restore a prefilled provider (from the "Add as Model" flow) once a
// compatible family is chosen.
const prefilledProviderId = (route.query.provider_id as string) || "";
watch(
  () => form.model_family_id,
  () => {
    const valid = providerItems.value.some((i) => i.value === form.provider_id);
    if (form.provider_id && !valid) form.provider_id = "";
    if (
      !form.provider_id &&
      prefilledProviderId &&
      providerItems.value.some((i) => i.value === prefilledProviderId)
    ) {
      form.provider_id = prefilledProviderId;
    }
  },
);

const canCreate = computed(
  () =>
    !!form.name.trim() &&
    !!form.model_identifier.trim() &&
    !!form.provider_id &&
    !!form.model_family_id,
);

function toggleEnabled() {
  form.enabled = !form.enabled;
}

async function handleCreate() {
  if (!canCreate.value) {
    toast.error("Name, identifier, provider, and family are all required");
    return;
  }
  try {
    const created = await createModel({
      name: form.name.trim(),
      model_identifier: form.model_identifier.trim(),
      provider_id: form.provider_id,
      model_family_id: form.model_family_id,
      use_openrouter: form.use_openrouter,
      openrouter_identifier: form.openrouter_identifier.trim() || null,
      enabled: form.enabled,
    });
    saved.value = true; // suppress the unsaved-changes guard on the redirect
    toast.success("Model created");
    router.push(`/settings/models/${created.id}`);
  } catch {
    toast.error("Failed to create model");
  }
}

function goBack() {
  router.push({ path: "/connections", query: { tab: "models" } });
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
      class="z-20 flex h-[60px] shrink-0 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-sm"
    >
      <div class="flex items-center gap-3">
        <button
          class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label="Back to models"
          @click="goBack"
        >
          <UIcon name="i-lucide-arrow-left" class="size-[18px]" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <UIcon name="i-lucide-cpu" class="size-3.5 text-primary-foreground" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            New Model
          </h1>
        </div>
      </div>

      <button
        class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96] disabled:pointer-events-none disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="handleCreate"
      >
        <UIcon
          :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
          class="size-4"
          :class="{ 'animate-spin': saving }"
        />
        {{ saving ? "Creating..." : "Create Model" }}
      </button>
    </header>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-2xl space-y-6">
        <!-- Identity card -->
        <div class="rounded-xl border bg-card/50 p-5">
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
                placeholder="Model display name"
                class="h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Model Identifier -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Model Identifier
              </span>
              <input
                v-model="form.model_identifier"
                type="text"
                placeholder="e.g. openai/gpt-4o"
                class="h-11 w-full rounded-lg border bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Model Family -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Model Family
              </span>
              <USelectMenu
                v-model="form.model_family_id"
                :items="familyItems"
                value-key="value"
                class="w-full"
                :ui="selectUi"
              >
                <button
                  class="flex h-11 w-full items-center rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30"
                >
                  {{ familyName }}
                </button>
              </USelectMenu>
            </label>

            <!-- Provider -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Provider
              </span>
              <USelectMenu
                v-model="form.provider_id"
                :items="providerItems"
                value-key="value"
                class="w-full"
                :ui="selectUi"
                :disabled="!form.model_family_id"
              >
                <button
                  :disabled="!form.model_family_id"
                  class="flex h-11 w-full items-center rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {{ form.model_family_id ? providerName : "Select a family first" }}
                </button>
              </USelectMenu>
            </label>

            <!-- OpenRouter routing -->
            <div class="rounded-lg border bg-muted/20 p-3">
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <span class="block text-sm text-foreground">Route via OpenRouter</span>
                  <span class="text-[10px] text-muted-foreground">
                    {{
                      canUseOpenrouter
                        ? "Available on OpenRouter"
                        : "Add an OpenRouter identifier below to enable"
                    }}
                  </span>
                </div>
                <button
                  role="switch"
                  :aria-checked="form.use_openrouter"
                  aria-label="Route via OpenRouter"
                  class="shrink-0 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!canUseOpenrouter"
                  @click="toggleUseOpenrouter"
                >
                  <div
                    class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                    :class="form.use_openrouter ? 'bg-primary' : 'bg-muted-foreground/40'"
                  >
                    <span
                      class="size-4 rounded-full shadow-sm transition-transform duration-300"
                      :class="
                        form.use_openrouter
                          ? 'translate-x-4 bg-background'
                          : 'translate-x-0 bg-white'
                      "
                    />
                  </div>
                </button>
              </div>
              <input
                v-model="form.openrouter_identifier"
                type="text"
                placeholder="OpenRouter identifier, e.g. openai/gpt-4o"
                class="mt-3 h-10 w-full rounded-lg border bg-muted/40 px-3 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </div>
          </div>
        </div>

        <!-- Options card -->
        <div class="rounded-xl border bg-card/50 p-5">
          <div class="flex items-center justify-between">
            <span class="text-sm text-muted-foreground">Enabled</span>
            <button
              role="switch"
              :aria-checked="form.enabled"
              aria-label="Enabled"
              class="cursor-pointer"
              @click="toggleEnabled"
            >
              <div
                class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                :class="form.enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
              >
                <span
                  class="size-4 rounded-full shadow-sm transition-transform duration-300"
                  :class="form.enabled ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
                />
              </div>
            </button>
          </div>
          <p class="mt-3 text-[11px] text-muted-foreground/70">
            Inference parameters can be tuned after the model is created.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
