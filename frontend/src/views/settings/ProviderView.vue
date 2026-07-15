<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useDebounceFn } from "@vueuse/core";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { useProvider } from "@/composables/useProvider";
import { useModels } from "@/composables/useModels";
import { useAppToast } from "@/composables/useToast";
import { useSettingsStore } from "@/stores/settings";
import { formatDate, timeAgo as timeAgoUtil } from "@/utils/date";
import { routeParam } from "@/utils/route";
import ModelCreateModal from "@/components/connections/ModelCreateModal.vue";
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
  searchResults,
  searchingModels,
  savingFilter,
  fetchAvailableModels,
  syncNow,
  searchModels,
  clearSearch,
  setModelFilter,
  loadModel,
  unloadModel,
  deleteModel,
} = useProvider();
const toast = useAppToast();
const settingsStore = useSettingsStore();

const isLocalProvider = computed(
  () => provider.value?.provider_type === "ollama" || provider.value?.provider_type === "lmstudio",
);

// Local providers (Ollama/LM Studio) have no API-key env var, so a green
// "configured" or an amber warning both mislead — present a neutral "Not set".
const apiKeyStatus = computed(() => {
  const p = provider.value;
  if (p && !p.env_var_name) {
    return {
      label: t("connections.provider.keyNotSet"),
      badge: "bg-base-300 text-muted-foreground",
      dot: "bg-muted-foreground/50",
    };
  }
  return p?.api_key_configured
    ? {
        label: t("connections.provider.keyConfigured"),
        badge: "bg-success/10 text-success",
        dot: "bg-success",
      }
    : {
        label: t("connections.provider.keyNotSet"),
        badge: "bg-warning/10 text-warning",
        dot: "bg-warning",
      };
});

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

// A discovered identifier counts as persisted when some registry has a route
// binding it to *this* provider — models are registries now, so the match is
// against each registry's embedded routes rather than a flat provider_id.
function isPersisted(modelIdentifier: string): boolean {
  return persistedModels.value.some((m) =>
    m.routes.some(
      (r) => r.provider_id === provider.value?.id && r.model_identifier === modelIdentifier,
    ),
  );
}

// --- Model filter (search + chips) ---
const modelSearchQuery = ref("");
const showSearchResults = ref(false);

const allowedModels = computed(() => provider.value?.allowed_models ?? []);

function isFiltered(identifier: string): boolean {
  return allowedModels.value.includes(identifier);
}

const debouncedSearch = useDebounceFn(async (q: string) => {
  if (!provider.value || !q.trim()) {
    clearSearch();
    return;
  }
  try {
    await searchModels(provider.value.id, q.trim());
    showSearchResults.value = true;
  } catch {
    // Search is advisory — a failure just leaves the dropdown empty.
  }
}, 250);

function onSearchInput() {
  if (modelSearchQuery.value.trim()) {
    showSearchResults.value = true;
    void debouncedSearch(modelSearchQuery.value);
  } else {
    showSearchResults.value = false;
    clearSearch();
  }
}

async function persistFilter(next: string[]) {
  if (!provider.value) return;
  try {
    await setModelFilter(provider.value.id, next);
  } catch {
    toast.error(t("connections.provider.toast.filterFailed"));
  }
}

async function addToFilter(identifier: string) {
  if (isFiltered(identifier)) return;
  await persistFilter([...allowedModels.value, identifier]);
  modelSearchQuery.value = "";
  showSearchResults.value = false;
  clearSearch();
}

async function removeFromFilter(identifier: string) {
  await persistFilter(allowedModels.value.filter((m) => m !== identifier));
}

async function clearFilter() {
  await persistFilter([]);
}

onMounted(async () => {
  const id = routeParam(route.params.id);
  // Independent (all keyed by id) — fetch in parallel so the page isn't gated
  // on three sequential round-trips.
  await Promise.all([
    fetchProvider(id),
    fetchAvailableModels(id),
    loadPersistedModels(1, { provider_id: id }),
  ]);
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
    toast.info(t("connections.provider.toast.noChanges"));
    return;
  }

  try {
    await saveProvider(provider.value.id, updates);
    // Refresh the shared provider cache so the Providers/Models tabs reflect the
    // edit instead of showing the stale pre-save name/URL/enabled state.
    await settingsStore.fetchProviders(true);
    toast.success(t("connections.provider.toast.updated"));
  } catch (e) {
    toast.error(t("connections.provider.toast.saveFailed"));
  }
}

function timeAgo(iso: string): string {
  return timeAgoUtil(iso, t);
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
    toast.success(t("connections.provider.toast.synced"));
  } catch (e) {
    toast.error(t("connections.provider.toast.syncFailed"));
  }
}

async function handleLoadModel(identifier: string) {
  if (!provider.value) return;
  if (!confirm(`Are you sure you want to load "${identifier}" into memory?`)) {
    return;
  }
  try {
    await loadModel(provider.value.id, identifier);
    toast.success(t("connections.provider.toast.modelLoaded", { model: identifier }));
  } catch (e) {
    toast.error(t("connections.provider.toast.loadFailed"));
  }
}

async function handleUnloadModel(identifier: string) {
  if (!provider.value) return;
  if (!confirm(`Are you sure you want to unload "${identifier}" from memory?`)) {
    return;
  }
  try {
    await unloadModel(provider.value.id, identifier);
    toast.success(t("connections.provider.toast.modelUnloaded", { model: identifier }));
  } catch (e) {
    toast.error(t("connections.provider.toast.unloadFailed"));
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
    toast.success(t("connections.provider.toast.modelDeleted", { model: identifier }));
    await loadPersistedModels(1, { provider_id: provider.value.id });
  } catch (e) {
    toast.error(e instanceof Error ? e.message : t("connections.provider.toast.deleteFailed"));
  }
}

// ── Add-as-Model modal (opens in place so cancelling leaves you here) ──
const showAddModel = ref(false);
const addModelPrefill = ref<
  { provider_id?: string; model_identifier?: string; name?: string } | undefined
>();

// Don't persist immediately — open the create form prefilled so the user can
// review, pick a model family, and confirm before it's saved.
function handleAddModel(m: { identifier: string; display_name?: string }) {
  if (!provider.value) return;
  addModelPrefill.value = {
    provider_id: provider.value.id,
    model_identifier: m.identifier,
    name: m.display_name || m.identifier,
  };
  showAddModel.value = true;
}

// Refresh the persisted list so the just-added model flips to "Added".
function onModelCreated() {
  if (provider.value) loadPersistedModels(1, { provider_id: provider.value.id });
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

    <template v-if="provider && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            :aria-label="$t('connections.provider.backToProviders')"
            @click="router.push({ path: '/connections', query: { tab: 'providers' } })"
          >
            <AppIcon name="i-lucide-arrow-left" class="size-5" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <AppIcon name="i-lucide-plug" class="size-3.5 text-primary-content" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Provider
            </h1>
          </div>
        </div>

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
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-2xl space-y-6">
          <!-- Main form card -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <!-- Provider type badge -->
            <div class="mb-5 flex items-center gap-3">
              <div class="flex size-10 items-center justify-center rounded-lg bg-base-300 p-2">
                <img
                  :src="getIcon(provider.provider_type)"
                  :alt="provider.provider_type"
                  class="size-full object-contain dark:invert"
                />
              </div>
              <div>
                <span
                  class="rounded-full bg-base-300 px-2.5 py-0.5 text-3xs font-medium tracking-wide text-foreground uppercase"
                >
                  {{ provider.provider_type }}
                </span>
                <p class="mt-0.5 text-3xs text-muted-foreground">Provider Type (read-only)</p>
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
                  class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
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
                  class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Enabled toggle -->
              <div class="flex items-center justify-between">
                <label
                  class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.provider.enabled") }}
                </label>
                <AppToggle
                  :model-value="form.enabled"
                  aria-label="Enabled"
                  @change="toggleEnabled"
                />
              </div>
            </div>
          </div>

          <!-- API Key section -->
          <div class="rounded-xl border bg-base-200/50 p-5">
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
                <code class="rounded bg-base-300 px-2 py-0.5 text-xs text-foreground">
                  {{ provider.env_var_name || "N/A" }}
                </code>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted-foreground">Status</span>
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="apiKeyStatus.badge"
                >
                  <span class="size-1.5 rounded-full" :class="apiKeyStatus.dot" />
                  {{ apiKeyStatus.label }}
                </span>
              </div>
            </div>
          </div>

          <!-- Available Models -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <h2
                  class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Available Models
                </h2>
                <p class="mt-0.5 text-3xs text-muted-foreground">
                  {{
                    provider.last_synced_at
                      ? `Last synced ${timeAgo(provider.last_synced_at)}`
                      : "Never synced"
                  }}
                </p>
              </div>
              <button
                class="flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium text-foreground transition-colors hover:bg-base-300 disabled:pointer-events-none disabled:opacity-50"
                :disabled="syncing"
                @click="handleSyncNow"
              >
                <AppIcon
                  :name="syncing ? 'i-lucide-loader-2' : 'i-lucide-refresh-cw'"
                  class="size-3.5"
                  :class="{ 'animate-spin': syncing }"
                />
                {{ syncing ? "Syncing..." : "Sync Now" }}
              </button>
            </div>

            <!-- Model filter: search + chips narrow the list below (empty = show all) -->
            <div class="mb-4 space-y-2">
              <div class="relative">
                <AppIcon
                  name="i-lucide-search"
                  class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <input
                  v-model="modelSearchQuery"
                  type="text"
                  placeholder="Search models to add to the filter…"
                  class="h-10 w-full rounded-lg border bg-base-300/40 pr-9 pl-9 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  @input="onSearchInput"
                  @focus="modelSearchQuery && (showSearchResults = true)"
                />
                <AppIcon
                  v-if="searchingModels"
                  name="i-lucide-loader-2"
                  class="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
                />

                <!-- Results dropdown -->
                <div
                  v-if="showSearchResults && modelSearchQuery"
                  class="absolute z-40 mt-1 w-full overflow-hidden rounded-lg border bg-base-200 shadow-lg"
                >
                  <div class="fixed inset-0 z-[-1]" @click="showSearchResults = false" />
                  <div
                    v-if="searchingModels && searchResults.length === 0"
                    class="px-3 py-2 text-xs text-muted-foreground"
                  >
                    Searching…
                  </div>
                  <div
                    v-else-if="searchResults.length === 0"
                    class="px-3 py-2 text-xs text-muted-foreground"
                  >
                    No matching models.
                  </div>
                  <ul v-else class="max-h-64 overflow-y-auto py-1">
                    <li v-for="r in searchResults" :key="r.identifier">
                      <button
                        class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left transition-colors hover:bg-base-300/60 disabled:cursor-not-allowed disabled:opacity-40"
                        :disabled="isFiltered(r.identifier) || savingFilter"
                        @click="addToFilter(r.identifier)"
                      >
                        <span class="min-w-0 truncate font-mono text-xs text-foreground">{{
                          r.identifier
                        }}</span>
                        <AppIcon
                          :name="isFiltered(r.identifier) ? 'i-lucide-check' : 'i-lucide-plus'"
                          class="size-3.5 shrink-0"
                          :class="
                            isFiltered(r.identifier) ? 'text-success' : 'text-muted-foreground'
                          "
                        />
                      </button>
                    </li>
                  </ul>
                </div>
              </div>

              <!-- Active filter chips -->
              <div v-if="allowedModels.length > 0" class="flex flex-wrap items-center gap-1.5">
                <span class="text-3xs tracking-wide text-muted-foreground uppercase">Filter:</span>
                <span
                  v-for="id in allowedModels"
                  :key="id"
                  class="inline-flex items-center gap-1 rounded-full bg-primary/10 py-0.5 pr-1 pl-2.5 text-2xs font-medium text-primary"
                >
                  <span class="max-w-55 truncate font-mono">{{ id }}</span>
                  <button
                    class="flex size-4 items-center justify-center rounded-full transition-colors hover:bg-primary/20 disabled:opacity-50"
                    :disabled="savingFilter"
                    aria-label="Remove from filter"
                    @click="removeFromFilter(id)"
                  >
                    <AppIcon name="i-lucide-x" class="size-3" />
                  </button>
                </span>
                <button
                  class="ml-1 text-3xs text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline disabled:opacity-50"
                  :disabled="savingFilter"
                  @click="clearFilter"
                >
                  Clear all
                </button>
              </div>
              <p v-else class="text-3xs text-muted-foreground">
                No filter set — showing all discovered models. Search above to show only specific
                ones.
              </p>
            </div>

            <div v-if="modelsLoading" class="flex justify-center py-6">
              <AppIcon name="i-lucide-loader-2" class="size-5 animate-spin text-muted-foreground" />
            </div>

            <div v-else-if="modelsError" class="flex flex-col items-center gap-2 py-6 text-center">
              <AppIcon name="i-lucide-alert-circle" class="size-5 text-error" />
              <p class="text-xs text-muted-foreground">{{ modelsError.message }}</p>
            </div>

            <div v-else-if="availableModels.length === 0" class="py-6 text-center">
              <p class="text-xs text-muted-foreground">
                {{
                  allowedModels.length > 0
                    ? "No discovered models match the current filter."
                    : "No models found on this server."
                }}
              </p>
            </div>

            <ul v-else class="space-y-2">
              <li
                v-for="model in availableModels"
                :key="model.identifier"
                class="relative flex items-center justify-between rounded-lg bg-base-300/40 px-3 py-2"
              >
                <div class="min-w-0 pr-4">
                  <p class="truncate text-sm text-foreground">{{ model.display_name }}</p>
                  <p class="text-3xs text-muted-foreground">
                    {{
                      [formatSize(model.size_bytes), model.quantization].filter(Boolean).join(" • ")
                    }}
                  </p>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <span
                    v-if="isLocalProvider"
                    class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-3xs font-medium"
                    :class="
                      model.state === 'loaded'
                        ? 'bg-success/10 text-success'
                        : 'bg-warning/10 text-warning'
                    "
                  >
                    <span
                      class="size-1.5 rounded-full"
                      :class="model.state === 'loaded' ? 'bg-success' : 'bg-warning'"
                    />
                    {{ model.state === "loaded" ? "Loaded" : "Not Loaded" }}
                  </span>

                  <!-- Context Dropdown Menu -->
                  <div class="relative">
                    <button
                      class="flex size-7 items-center justify-center rounded-md border text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
                      :disabled="pendingModelAction === model.identifier"
                      @click.stop="toggleMenu(model.identifier)"
                    >
                      <AppIcon
                        v-if="pendingModelAction === model.identifier"
                        name="i-lucide-loader-2"
                        class="size-3.5 animate-spin"
                      />
                      <AppIcon v-else name="i-lucide-ellipsis-vertical" class="size-3.5" />
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
                        class="absolute top-full right-0 z-50 mt-1 w-44 origin-top-right rounded-lg border bg-base-200 py-1 shadow-lg"
                      >
                        <!-- Click outside handler overlay -->
                        <div class="fixed inset-0 z-[-1]" @click.stop="openMenuModel = null" />

                        <!-- Load / Unload option -->
                        <button
                          v-if="isLocalProvider"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-base-content transition-colors hover:bg-base-300/60"
                          @click="
                            openMenuModel = null;
                            model.state === 'loaded'
                              ? handleUnloadModel(model.identifier)
                              : handleLoadModel(model.identifier);
                          "
                        >
                          <AppIcon
                            :name="model.state === 'loaded' ? 'i-lucide-square' : 'i-lucide-play'"
                            class="size-3.5"
                          />
                          {{ model.state === "loaded" ? "Unload Model" : "Load Model" }}
                        </button>

                        <!-- Add as model (opens the create form prefilled) -->
                        <button
                          v-if="!isPersisted(model.identifier)"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-base-content transition-colors hover:bg-base-300/60"
                          @click="
                            openMenuModel = null;
                            handleAddModel(model);
                          "
                        >
                          <AppIcon name="i-lucide-plus" class="size-3.5" />
                          Add as Model…
                        </button>
                        <div
                          v-else
                          class="flex w-full cursor-not-allowed items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground/60"
                        >
                          <AppIcon name="i-lucide-check" class="size-3.5 text-success" />
                          Added
                        </div>

                        <!-- Delete option (Ollama only) -->
                        <button
                          v-if="provider.provider_type === 'ollama'"
                          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-error transition-colors hover:bg-error/10"
                          @click="
                            openMenuModel = null;
                            handleDeleteModel(model.identifier);
                          "
                        >
                          <AppIcon name="i-lucide-trash-2" class="size-3.5" />
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
          <div class="flex items-center justify-between px-1 text-2xs text-muted-foreground/60">
            <span>Created {{ formatDate(provider.created_at) }}</span>
            <span>Updated {{ formatDate(provider.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- Add-as-Model create modal (opens in place; cancel stays on this page) -->
    <ModelCreateModal
      :show="showAddModel"
      :prefill="addModelPrefill"
      @close="showAddModel = false"
      @created="onModelCreated"
    />
  </div>
</template>
