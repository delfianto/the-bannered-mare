<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { useProvider } from "@/composables/useProvider";
import { useModels } from "@/composables/useModels";
import { useAppToast } from "@/composables/useToast";
import anthropicIcon from "@/assets/icons/anthropic.svg";
import googleIcon from "@/assets/icons/google.svg";
import ollamaIcon from "@/assets/icons/ollama.svg";
import openaiIcon from "@/assets/icons/openai.svg";
import openrouterIcon from "@/assets/icons/openrouter.svg";
import xaiIcon from "@/assets/icons/xai.svg";
import otherIcon from "@/assets/icons/other.svg";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const {
  provider,
  loading,
  saving,
  error,
  fetchProvider,
  saveProvider,
  availableModels,
  modelsLoading,
  syncing,
  modelsError,
  pendingModelAction,
  fetchAvailableModels,
  syncNow,
  loadModel,
  unloadModel,
  deleteModel,
  persistModel,
} = useProvider();
const toast = useAppToast();

const isLocalProvider = computed(
  () => provider.value?.provider_type === "ollama" || provider.value?.provider_type === "lmstudio",
);

const providerIcons: Record<string, string> = {
  openai: openaiIcon,
  anthropic: anthropicIcon,
  google: googleIcon,
  ollama: ollamaIcon,
  openrouter: openrouterIcon,
  xai: xaiIcon,
  custom: otherIcon,
};

function getIcon(providerType: string): string {
  return providerIcons[providerType] || otherIcon;
}

const form = reactive({
  name: "",
  base_url: "",
  enabled: true,
});

const { models: persistedModels, loadPage: loadPersistedModels } = useModels({ pageSize: 100 });

function isPersisted(modelIdentifier: string): boolean {
  return persistedModels.value.some(
    (m) => m.model_identifier === modelIdentifier && m.provider_id === provider.value?.id,
  );
}

onMounted(async () => {
  const id = route.params.id as string;
  await fetchProvider(id);
  await fetchAvailableModels(id);
  await loadPersistedModels(1, { provider_id: id });
});

watch(provider, (p) => {
  if (p) {
    form.name = p.name;
    form.base_url = p.base_url || "";
    form.enabled = p.enabled;
  }
});

function toggleEnabled() {
  form.enabled = !form.enabled;
}

async function handleSave() {
  if (!provider.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== provider.value.name) updates.name = form.name;
  if (form.base_url !== (provider.value.base_url || "")) updates.base_url = form.base_url || null;
  if (form.enabled !== provider.value.enabled) updates.enabled = form.enabled;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await saveProvider(provider.value.id, updates);
    toast.success("Provider updated");
  } catch (e) {
    toast.error("Failed to save provider");
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t("time.justNow");
  if (mins < 60) return t("time.minutesAgo", { count: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t("time.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  return t("time.daysAgo", { count: days });
}

function formatSize(bytes: number | null | undefined): string | null {
  if (!bytes) return null;
  const gb = bytes / 1024 ** 3;
  return `${gb.toFixed(1)} GB`;
}

async function handleSyncNow() {
  if (!provider.value) return;
  try {
    await syncNow(provider.value.id);
    toast.success("Model list synced");
  } catch (e) {
    toast.error("Failed to sync models");
  }
}

async function handleLoadModel(identifier: string) {
  if (!provider.value) return;
  if (!confirm(`Are you sure you want to load "${identifier}" into memory?`)) {
    return;
  }
  try {
    await loadModel(provider.value.id, identifier);
    toast.success(`Loaded ${identifier}`);
  } catch (e) {
    toast.error("Failed to load model");
  }
}

async function handleUnloadModel(identifier: string) {
  if (!provider.value) return;
  if (!confirm(`Are you sure you want to unload "${identifier}" from memory?`)) {
    return;
  }
  try {
    await unloadModel(provider.value.id, identifier);
    toast.success(`Unloaded ${identifier}`);
  } catch (e) {
    toast.error("Failed to unload model");
  }
}

async function handleDeleteModel(identifier: string) {
  if (!provider.value) return;
  if (
    !confirm(
      `Are you sure you want to delete model "${identifier}" from the provider server? This cannot be undone.`,
    )
  ) {
    return;
  }
  try {
    await deleteModel(provider.value.id, identifier);
    toast.success(`Deleted ${identifier}`);
    await loadPersistedModels(1, { provider_id: provider.value.id });
  } catch (e) {
    toast.error(e instanceof Error ? e.message : "Failed to delete model");
  }
}

async function handlePersistModel(identifier: string) {
  if (!provider.value) return;
  try {
    await persistModel(provider.value.id, identifier);
    toast.success(`Persisted definition for ${identifier}`);
    await loadPersistedModels(1, { provider_id: provider.value.id });
  } catch (e) {
    toast.error("Failed to persist model definition");
  }
}

const openMenuModel = ref<string | null>(null);

function toggleMenu(identifier: string) {
  if (openMenuModel.value === identifier) {
    openMenuModel.value = null;
  } else {
    openMenuModel.value = identifier;
  }
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
        <UIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">{{ $t("common.loading") }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <UIcon name="i-lucide-alert-circle" class="size-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="router.back()"
      >
        {{ $t("common.goBack") }}
      </button>
    </div>

    <template v-if="provider && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-[60px] shrink-0 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            :aria-label="$t('connections.provider.backToProviders')"
            @click="router.push({ path: '/connections', query: { tab: 'providers' } })"
          >
            <UIcon name="i-lucide-arrow-left" class="size-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-plug" class="size-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Provider
            </h1>
          </div>
        </div>

        <button
          class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
          :disabled="saving"
          @click="handleSave"
        >
          <UIcon
            :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
            class="size-4"
            :class="{ 'animate-spin': saving }"
          />
          {{ saving ? $t("common.saving") : $t("common.save") }}
        </button>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-2xl space-y-6">
          <!-- Main form card -->
          <div class="rounded-xl border bg-card/50 p-5">
            <!-- Provider type badge -->
            <div class="mb-5 flex items-center gap-3">
              <div class="flex size-10 items-center justify-center rounded-lg bg-accent p-2">
                <img
                  :src="getIcon(provider.provider_type)"
                  :alt="provider.provider_type"
                  class="size-full object-contain dark:invert"
                />
              </div>
              <div>
                <span
                  class="rounded-full bg-accent px-2.5 py-0.5 text-[10px] font-medium tracking-wide text-foreground uppercase"
                >
                  {{ provider.provider_type }}
                </span>
                <p class="mt-0.5 text-[10px] text-muted-foreground">Provider Type (read-only)</p>
              </div>
            </div>

            <div class="space-y-4">
              <!-- Name -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.provider.name") }}
                </span>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Provider name"
                  class="h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Base URL -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.provider.baseUrl") }}
                </span>
                <input
                  v-model="form.base_url"
                  type="text"
                  placeholder="https://api.example.com/v1"
                  class="h-11 w-full rounded-lg border bg-muted/40 px-4 font-mono text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Enabled toggle -->
              <div class="flex items-center justify-between">
                <label
                  class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.provider.enabled") }}
                </label>
                <button
                  role="switch"
                  :aria-checked="form.enabled"
                  aria-label="Enabled"
                  class="cursor-pointer"
                  @click="toggleEnabled"
                >
                  <div
                    class="flex h-[22px] w-10 items-center rounded-full px-[3px]"
                    :class="form.enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
                  >
                    <span
                      class="size-4 rounded-full shadow-sm transition-transform"
                      :class="
                        form.enabled ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'
                      "
                    />
                  </div>
                </button>
              </div>
            </div>
          </div>

          <!-- API Key section -->
          <div class="rounded-xl border bg-card/50 p-5">
            <h2
              class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.provider.apiKey") }}
            </h2>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted-foreground">{{
                  $t("connections.provider.envVar")
                }}</span>
                <code class="rounded bg-accent px-2 py-0.5 text-xs text-foreground">
                  {{ provider.env_var_name || "N/A" }}
                </code>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted-foreground">Status</span>
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    provider.api_key_configured
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : 'bg-amber-500/10 text-amber-500'
                  "
                >
                  <span
                    class="size-1.5 rounded-full"
                    :class="provider.api_key_configured ? 'bg-emerald-500' : 'bg-amber-500'"
                  />
                  {{
                    provider.api_key_configured
                      ? $t("connections.provider.keyConfigured")
                      : $t("connections.provider.keyNotSet")
                  }}
                </span>
              </div>
            </div>
          </div>

          <!-- Available Models -->
          <div class="rounded-xl border bg-card/50 p-5">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <h2
                  class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Available Models
                </h2>
                <p class="mt-0.5 text-[10px] text-muted-foreground">
                  {{
                    provider.last_synced_at
                      ? `Last synced ${timeAgo(provider.last_synced_at)}`
                      : "Never synced"
                  }}
                </p>
              </div>
              <button
                class="flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-50"
                :disabled="syncing"
                @click="handleSyncNow"
              >
                <UIcon
                  :name="syncing ? 'i-lucide-loader-2' : 'i-lucide-refresh-cw'"
                  class="size-3.5"
                  :class="{ 'animate-spin': syncing }"
                />
                {{ syncing ? "Syncing..." : "Sync Now" }}
              </button>
            </div>

            <div v-if="modelsLoading" class="flex justify-center py-6">
              <UIcon name="i-lucide-loader-2" class="size-5 animate-spin text-muted-foreground" />
            </div>

            <div v-else-if="modelsError" class="flex flex-col items-center gap-2 py-6 text-center">
              <UIcon name="i-lucide-alert-circle" class="size-5 text-destructive" />
              <p class="text-xs text-muted-foreground">{{ modelsError.message }}</p>
            </div>

            <div v-else-if="availableModels.length === 0" class="py-6 text-center">
              <p class="text-xs text-muted-foreground">No models found on this server.</p>
            </div>

            <ul v-else class="space-y-2">
              <li
                v-for="model in availableModels"
                :key="model.identifier"
                class="relative flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2"
              >
                <div class="min-w-0 pr-4">
                  <p class="truncate text-sm text-foreground">{{ model.display_name }}</p>
                  <p class="text-[10px] text-muted-foreground">
                    {{
                      [formatSize(model.size_bytes), model.quantization].filter(Boolean).join(" • ")
                    }}
                  </p>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <span
                    v-if="isLocalProvider"
                    class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium"
                    :class="
                      model.state === 'loaded'
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : 'bg-amber-500/10 text-amber-500'
                    "
                  >
                    <span
                      class="size-1.5 rounded-full"
                      :class="model.state === 'loaded' ? 'bg-emerald-500' : 'bg-amber-500'"
                    />
                    {{ model.state === "loaded" ? "Loaded" : "Not Loaded" }}
                  </span>

                  <!-- Context Dropdown Menu -->
                  <div class="relative">
                    <button
                      class="flex size-7 items-center justify-center rounded-md border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
                      :disabled="pendingModelAction === model.identifier"
                      @click.stop="toggleMenu(model.identifier)"
                    >
                      <UIcon
                        v-if="pendingModelAction === model.identifier"
                        name="i-lucide-loader-2"
                        class="size-3.5 animate-spin"
                      />
                      <UIcon v-else name="i-lucide-ellipsis-vertical" class="size-3.5" />
                    </button>

                    <Transition
                      enter-active-class="transition duration-150 ease-out"
                      enter-from-class="scale-95 opacity-0"
                      enter-to-class="scale-100 opacity-100"
                      leave-active-class="transition duration-100 ease-in"
                      leave-from-class="scale-100 opacity-100"
                      leave-to-class="scale-95 opacity-0"
                    >
                      <div
                        v-if="openMenuModel === model.identifier"
                        class="absolute top-full right-0 z-50 mt-1 w-44 origin-top-right rounded-lg border bg-popover py-1 shadow-lg"
                      >
                        <!-- Click outside handler overlay -->
                        <div class="fixed inset-0 z-[-1]" @click.stop="openMenuModel = null" />

                        <!-- Load / Unload option -->
                        <button
                          v-if="isLocalProvider"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-popover-foreground transition-colors hover:bg-muted/60"
                          @click="
                            openMenuModel = null;
                            model.state === 'loaded'
                              ? handleUnloadModel(model.identifier)
                              : handleLoadModel(model.identifier);
                          "
                        >
                          <UIcon
                            :name="model.state === 'loaded' ? 'i-lucide-square' : 'i-lucide-play'"
                            class="size-3.5"
                          />
                          {{ model.state === "loaded" ? "Unload Model" : "Load Model" }}
                        </button>

                        <!-- Persist option -->
                        <button
                          v-if="!isPersisted(model.identifier)"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-popover-foreground transition-colors hover:bg-muted/60"
                          @click="
                            openMenuModel = null;
                            handlePersistModel(model.identifier);
                          "
                        >
                          <UIcon name="i-lucide-database-backup" class="size-3.5" />
                          Persist Definition
                        </button>
                        <div
                          v-else
                          class="flex w-full cursor-not-allowed items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground/60"
                        >
                          <UIcon name="i-lucide-check" class="size-3.5 text-emerald-500" />
                          Persisted
                        </div>

                        <!-- Delete option (Ollama only) -->
                        <button
                          v-if="provider.provider_type === 'ollama'"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-destructive transition-colors hover:bg-destructive/10"
                          @click="
                            openMenuModel = null;
                            handleDeleteModel(model.identifier);
                          "
                        >
                          <UIcon name="i-lucide-trash-2" class="size-3.5" />
                          Delete Model
                        </button>
                      </div>
                    </Transition>
                  </div>
                </div>
              </li>
            </ul>
          </div>

          <!-- Timestamps -->
          <div class="flex items-center justify-between px-1 text-[11px] text-muted-foreground/60">
            <span>Created {{ formatDate(provider.created_at) }}</span>
            <span>Updated {{ formatDate(provider.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
