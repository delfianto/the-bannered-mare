<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useModel } from "@/composables/useModel";
import { useSettingsStore } from "@/stores/settings";
import { useAppToast } from "@/composables/useToast";
import ModelInferenceParams from "@/components/connections/ModelInferenceParams.vue";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { providersForFamily } from "@/utils/modelProviderFilter";

const router = useRouter();
const route = useRoute();
const { model, loading, saving, deleting, error, fetchModel, saveModel, deleteModel } = useModel();
const { families } = useModelFamilies({ pageSize: 100 });
const settingsStore = useSettingsStore();
const toast = useAppToast();

const confirmDelete = ref(false);

const form = reactive({
  name: "",
  model_identifier: "",
  provider_id: "",
  model_family_id: "",
  use_openrouter: false,
  openrouter_identifier: "",
  enabled: true,
  parameters: {} as Record<string, unknown>,
});

onMounted(async () => {
  const id = route.params.id as string;
  await Promise.all([
    fetchModel(id),
    settingsStore.fetchProviders(),
    settingsStore.fetchParameterDocs(),
  ]);
});

watch(model, (m) => {
  if (m) {
    form.name = m.name;
    form.model_identifier = m.model_identifier;
    form.provider_id = m.provider_id;
    form.model_family_id = m.model_family_id;
    form.use_openrouter = m.use_openrouter;
    form.openrouter_identifier = m.openrouter_identifier || "";
    form.enabled = m.enabled;
    form.parameters = m.parameters ? { ...m.parameters } : {};
  }
});

const familyParameters = computed(() => {
  if (!model.value?.model_family?.parameters) return {};
  return model.value.model_family.parameters as Record<string, any>;
});

function toggleEnabled() {
  form.enabled = !form.enabled;
}

function onUpdateParameters(params: Record<string, unknown>) {
  form.parameters = params;
}

// A model is available on OpenRouter iff it has an OpenRouter identifier.
const canUseOpenrouter = computed(() => !!form.openrouter_identifier.trim());

function toggleUseOpenrouter() {
  if (!canUseOpenrouter.value) return;
  form.use_openrouter = !form.use_openrouter;
}

// Clearing the identifier makes it unroutable — turn routing off to stay consistent.
watch(
  () => form.openrouter_identifier,
  (v) => {
    if (!v.trim()) form.use_openrouter = false;
  },
);

// Drop a provider that the newly chosen family can't serve.
watch(
  () => form.model_family_id,
  () => {
    if (form.provider_id && !providerItems.value.some((i) => i.value === form.provider_id)) {
      form.provider_id = "";
    }
  },
);

const selectedFamily = computed(
  () =>
    families.value.find((f: any) => f.id === form.model_family_id) ||
    (model.value?.model_family as any),
);
const providerItems = computed(() =>
  providersForFamily(settingsStore.providers as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...families.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);

const providerName = computed(() => {
  const provider = settingsStore.providers.find((p: any) => p.id === form.provider_id);
  return provider?.name || form.provider_id;
});
const familyName = computed(
  () =>
    familyItems.value.find((i) => i.value === form.model_family_id)?.label ||
    model.value?.model_family?.name ||
    form.model_family_id,
);

async function handleSave() {
  if (!model.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== model.value.name) updates.name = form.name;
  if (form.model_identifier !== model.value.model_identifier)
    updates.model_identifier = form.model_identifier;
  if (form.provider_id !== model.value.provider_id) updates.provider_id = form.provider_id;
  if (form.model_family_id !== model.value.model_family_id)
    updates.model_family_id = form.model_family_id;
  if (form.use_openrouter !== model.value.use_openrouter)
    updates.use_openrouter = form.use_openrouter;
  if ((form.openrouter_identifier || "") !== (model.value.openrouter_identifier || ""))
    updates.openrouter_identifier = form.openrouter_identifier || null;
  if (form.enabled !== model.value.enabled) updates.enabled = form.enabled;
  if (JSON.stringify(form.parameters) !== JSON.stringify(model.value.parameters ?? {}))
    updates.parameters = form.parameters;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    const id = model.value.id;
    await saveModel(id, updates);
    // Re-fetch the full detail so the embedded model_family (and its parameter
    // schema) reflect any family change — the PUT response omits it.
    await fetchModel(id);
    toast.success("Model updated");
  } catch (e) {
    toast.error("Failed to save model");
  }
}

async function handleDelete() {
  if (!model.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
    return;
  }
  try {
    await deleteModel(model.value.id);
    toast.success("Model deleted");
    router.push({ path: "/connections", query: { tab: "models" } });
  } catch (e) {
    toast.error("Failed to delete model");
    confirmDelete.value = false;
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Loading overlay -->
    <div
      v-if="loading"
      class="absolute inset-0 z-50 flex items-center justify-center bg-base-100/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">{{ $t("common.loading") }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="router.back()"
      >
        {{ $t("common.goBack") }}
      </button>
    </div>

    <template v-if="model && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            :aria-label="$t('connections.model.backToModels')"
            @click="router.push({ path: '/connections', query: { tab: 'models' } })"
          >
            <AppIcon name="i-lucide-arrow-left" class="size-5" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <AppIcon name="i-lucide-cpu" class="size-3.5 text-primary-content" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Model
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Delete button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg border px-4 text-sm font-medium transition-colors"
            :class="
              confirmDelete
                ? 'border-error bg-error/10 text-error'
                : 'border-error/30 text-error hover:bg-error/10'
            "
            :disabled="deleting"
            @click="handleDelete"
          >
            <AppIcon
              :name="deleting ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
              class="size-4"
              :class="{ 'animate-spin': deleting }"
            />
            {{
              deleting
                ? $t("common.deleting")
                : confirmDelete
                  ? $t("common.deleteConfirm")
                  : $t("common.delete")
            }}
          </button>

          <!-- Save button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
            :disabled="saving"
            @click="handleSave"
          >
            <AppIcon
              :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
              class="size-4"
              :class="{ 'animate-spin': saving }"
            />
            {{ saving ? $t("common.saving") : $t("common.save") }}
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-5">
          <!-- Left column (3 cols) -->
          <div class="space-y-6 lg:col-span-3">
            <!-- Identity card -->
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
                    {{ $t("connections.model.name") }}
                  </span>
                  <input
                    v-model="form.name"
                    type="text"
                    placeholder="Model display name"
                    class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Model Identifier -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                  >
                    {{ $t("connections.model.identifier") }}
                  </span>
                  <input
                    v-model="form.model_identifier"
                    type="text"
                    placeholder="e.g. gpt-4o, claude-4.5-sonnet"
                    class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Model Family -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                  >
                    {{ $t("connections.model.family") }}
                  </span>
                  <SelectMenu
                    v-model="form.model_family_id"
                    :items="familyItems"
                    value-key="value"
                    class="w-full"
                  >
                    <button
                      class="flex h-11 w-full items-center rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none hover:border-muted-foreground/30"
                    >
                      {{ familyName }}
                    </button>
                  </SelectMenu>
                </label>

                <!-- Provider selector -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                  >
                    {{ $t("connections.model.provider") }}
                  </span>
                  <SelectMenu
                    v-model="form.provider_id"
                    :items="providerItems"
                    value-key="value"
                    :search-input="false"
                    class="w-full"
                    :disabled="!form.model_family_id"
                  >
                    <button
                      class="flex h-11 w-full items-center rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none hover:border-muted-foreground/30 disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="!form.model_family_id"
                    >
                      {{ providerName }}
                    </button>
                  </SelectMenu>
                </label>

                <!-- OpenRouter routing -->
                <div class="rounded-lg border bg-base-300/20 p-3">
                  <div class="flex items-center justify-between gap-3">
                    <div class="min-w-0">
                      <span class="block text-sm text-foreground">Route via OpenRouter</span>
                      <span class="text-[0.625rem] text-muted-foreground">
                        {{
                          canUseOpenrouter
                            ? "Available on OpenRouter"
                            : "Add an OpenRouter identifier below to enable"
                        }}
                      </span>
                    </div>
                    <AppToggle
                      class="shrink-0"
                      :model-value="form.use_openrouter"
                      :disabled="!canUseOpenrouter"
                      aria-label="Route via OpenRouter"
                      @change="toggleUseOpenrouter"
                    />
                  </div>
                  <input
                    v-model="form.openrouter_identifier"
                    type="text"
                    placeholder="OpenRouter identifier, e.g. openai/gpt-4o"
                    class="mt-3 h-10 w-full rounded-lg border bg-base-300/40 px-3 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </div>
              </div>
            </div>

            <!-- Inference Parameters card -->
            <div class="rounded-xl border bg-base-200/50 p-5">
              <h2
                class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                {{ $t("connections.model.inferenceParams") }}
              </h2>
              <ModelInferenceParams
                :family-parameters="familyParameters"
                :model-parameters="form.parameters"
                :parameter-docs="settingsStore.parameterDocs"
                @update:model-parameters="onUpdateParameters"
              />
            </div>
          </div>

          <!-- Right column (2 cols) -->
          <div class="space-y-6 lg:col-span-2">
            <!-- Metadata card -->
            <div class="rounded-xl border bg-base-200/50 p-5">
              <h2
                class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                {{ $t("connections.model.metadata") }}
              </h2>
              <div class="space-y-3">
                <!-- Enabled toggle -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">{{
                    $t("connections.model.enabled")
                  }}</span>
                  <AppToggle
                    :model-value="form.enabled"
                    aria-label="Enabled"
                    @change="toggleEnabled"
                  />
                </div>

                <div class="h-px bg-border/50" />

                <!-- Provider status -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">{{
                    $t("connections.model.provider")
                  }}</span>
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm text-foreground">{{ providerName }}</span>
                    <span
                      class="size-2 rounded-full"
                      :class="model.provider_enabled ? 'bg-emerald-500' : 'bg-red-500'"
                    />
                  </div>
                </div>

                <!-- Active Identifier -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Active Identifier</span>
                  <code
                    class="max-w-50 truncate rounded bg-base-300 px-2 py-0.5 text-xs text-foreground"
                  >
                    {{ model.active_identifier }}
                  </code>
                </div>

                <!-- Timestamps -->
                <div class="border-t border-border/50 pt-3">
                  <div class="space-y-1.5 text-[0.6875rem] text-muted-foreground/60">
                    <div class="flex justify-between">
                      <span>Created</span>
                      <span>{{ formatDate(model.created_at) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>Updated</span>
                      <span>{{ formatDate(model.updated_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
