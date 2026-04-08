<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useModel } from "@/composables/useModel";
import { useSettingsStore } from "@/stores/settings";
import { useAppToast } from "@/composables/useToast";
import ModelInferenceParams from "@/components/connections/ModelInferenceParams.vue";

const router = useRouter();
const route = useRoute();
const { model, loading, saving, deleting, error, fetchModel, saveModel, deleteModel } = useModel();
const settingsStore = useSettingsStore();
const toast = useAppToast();

const confirmDelete = ref(false);

const form = reactive({
  name: "",
  model_identifier: "",
  provider_id: "",
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

// Filter providers by the model family's supported provider_types
const allowedProviders = computed(() => {
  const familyTypes = (model.value?.model_family as any)?.provider_types as string[] | undefined;
  if (!familyTypes || familyTypes.length === 0) return settingsStore.providers;
  return settingsStore.providers.filter((p: any) => familyTypes.includes(p.provider_type));
});

const providerName = computed(() => {
  const provider = settingsStore.providers.find((p: any) => p.id === form.provider_id);
  return provider?.name || form.provider_id;
});

async function handleSave() {
  if (!model.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== model.value.name) updates.name = form.name;
  if (form.model_identifier !== model.value.model_identifier) updates.model_identifier = form.model_identifier;
  if (form.provider_id !== model.value.provider_id) updates.provider_id = form.provider_id;
  if (form.enabled !== model.value.enabled) updates.enabled = form.enabled;
  // Always include parameters (hard to diff deeply)
  updates.parameters = form.parameters;

  try {
    await saveModel(model.value.id, updates);
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
      class="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">Loading model...</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="router.back()"
      >
        Go Back
      </button>
    </div>

    <template v-if="model && !loading">
      <!-- Header -->
      <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="router.push({ path: '/connections', query: { tab: 'models' } })"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-cpu" class="h-3.5 w-3.5 text-primary-foreground" />
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
                ? 'border-destructive bg-destructive/10 text-destructive'
                : 'border-destructive/30 text-destructive hover:bg-destructive/10'
            "
            :disabled="deleting"
            @click="handleDelete"
          >
            <UIcon
              :name="deleting ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
              class="h-4 w-4"
              :class="{ 'animate-spin': deleting }"
            />
            {{ deleting ? "Deleting..." : confirmDelete ? "Confirm?" : "Delete" }}
          </button>

          <!-- Save button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
            :disabled="saving"
            @click="handleSave"
          >
            <UIcon
              :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
              class="h-4 w-4"
              :class="{ 'animate-spin': saving }"
            />
            {{ saving ? "Saving..." : "Save" }}
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-5">
          <!-- Left column (3 cols) -->
          <div class="space-y-6 lg:col-span-3">
            <!-- Identity card -->
            <div class="rounded-xl border border-border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Identity
              </h2>
              <div class="space-y-4">
                <!-- Name -->
                <div>
                  <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    Name
                  </label>
                  <input
                    v-model="form.name"
                    type="text"
                    placeholder="Model display name"
                    class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </div>

                <!-- Model Identifier -->
                <div>
                  <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    Model Identifier
                  </label>
                  <input
                    v-model="form.model_identifier"
                    type="text"
                    placeholder="e.g. gpt-4o, claude-4.5-sonnet"
                    class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </div>

                <!-- Provider selector -->
                <div>
                  <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    Provider
                  </label>
                  <USelectMenu
                    v-if="allowedProviders.length > 1"
                    v-model="form.provider_id"
                    :items="allowedProviders.map((p: any) => ({ label: p.name, value: p.id }))"
                    value-key="value"
                    :search-input="false"
                    class="w-full"
                    :ui="{
                      base: 'w-full border-none shadow-none ring-0 outline-none p-0 bg-transparent',
                      content: 'w-[var(--reka-popper-anchor-width)] border border-border bg-card ring-0 outline-none shadow-lg',
                      item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
                    }"
                  >
                    <button
                      class="flex h-11 w-full items-center rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30"
                    >
                      {{ providerName }}
                    </button>
                  </USelectMenu>
                  <!-- Single provider — show as read-only -->
                  <div
                    v-else
                    class="flex h-11 w-full items-center rounded-lg border border-border bg-muted/20 px-4 text-sm text-muted-foreground"
                  >
                    {{ providerName }}
                    <span class="ml-auto text-[10px] text-muted-foreground/60">Only compatible provider</span>
                  </div>
                </div>



              </div>
            </div>

            <!-- Inference Parameters card -->
            <div class="rounded-xl border border-border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Inference Parameters
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
            <div class="rounded-xl border border-border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Metadata
              </h2>
              <div class="space-y-3">
                <!-- Enabled toggle -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Enabled</span>
                  <button @click="toggleEnabled" class="cursor-pointer">
                    <div
                      class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                      :class="form.enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
                    >
                      <span
                        class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
                        :class="form.enabled ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
                      />
                    </div>
                  </button>
                </div>

                <div class="h-px bg-border/50" />

                <!-- Model Family -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Model Family</span>
                  <button
                    class="text-sm text-primary hover:underline"
                    @click="router.push(`/settings/model-families/${model.model_family_id}`)"
                  >
                    {{ model.model_family?.name || model.model_family_id }}
                  </button>
                </div>

                <!-- Provider status -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Provider</span>
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm text-foreground">{{ providerName }}</span>
                    <span
                      class="h-2 w-2 rounded-full"
                      :class="model.provider_enabled ? 'bg-emerald-500' : 'bg-red-500'"
                    />
                  </div>
                </div>

                <!-- Active Identifier -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Active Identifier</span>
                  <code class="max-w-[200px] truncate rounded bg-accent px-2 py-0.5 text-xs text-foreground">
                    {{ model.active_identifier }}
                  </code>
                </div>

                <!-- OpenRouter capability -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">OpenRouter</span>
                  <span
                    class="text-xs"
                    :class="model.can_use_openrouter ? 'text-emerald-500' : 'text-muted-foreground'"
                  >
                    {{ model.can_use_openrouter ? "Available" : "Not Available" }}
                  </span>
                </div>

                <!-- Timestamps -->
                <div class="border-t border-border/50 pt-3">
                  <div class="space-y-1.5 text-[11px] text-muted-foreground/60">
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
