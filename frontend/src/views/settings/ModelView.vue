<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { useModel } from "@/composables/useModel";
import { useSettingsStore } from "@/stores/settings";
import { useAppToast } from "@/composables/useToast";
import ModelInferenceParams from "@/components/connections/ModelInferenceParams.vue";
import AppTooltip from "@/components/shared/AppTooltip.vue";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { providersForFamily } from "@/utils/modelProviderFilter";

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const {
  model,
  loading,
  saving,
  deleting,
  error,
  fetchModel,
  saveModel,
  deleteModel,
  addRoute,
  deleteRoute,
  setActiveRoute,
} = useModel();
const { families } = useModelFamilies({ pageSize: 100 });
const settingsStore = useSettingsStore();
const toast = useAppToast();

const confirmDelete = ref(false);

// The identity form edits registry fields only — a model's provider bindings
// live in its routes and are managed via the Routes card below.
const form = reactive({
  display_name: "",
  model_family_id: "",
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
    form.display_name = m.display_name;
    form.model_family_id = m.model_family_id;
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

const selectedFamily = computed(
  () =>
    families.value.find((f: any) => f.id === form.model_family_id) ||
    (model.value?.model_family as any),
);
const familyItems = computed(() =>
  [...families.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);
const familyName = computed(
  () =>
    familyItems.value.find((i) => i.value === form.model_family_id)?.label ||
    model.value?.model_family?.name ||
    form.model_family_id,
);

// ── Routes (the provider bindings) ───────────────────────
function providerFor(id: string) {
  return settingsStore.providers.find((p: any) => p.id === id);
}
function providerName(id: string): string {
  return (providerFor(id) as any)?.name || id;
}
function identifierHintFor(id: string): string {
  return (providerFor(id) as any)?.identifier_hint || "";
}

const routes = computed(() => model.value?.routes ?? []);
const activeRouteId = computed(() => model.value?.active_route_id ?? routes.value[0]?.id ?? null);
const activeRoute = computed(
  () => routes.value.find((r) => r.id === activeRouteId.value) ?? routes.value[0] ?? null,
);
const activeProvider = computed(() =>
  activeRoute.value ? providerFor(activeRoute.value.provider_id) : null,
);
const activeProviderName = computed(() => (activeProvider.value as any)?.name || "—");
// The identifier scheme is provider-specific (the provider is the route):
// surface the active route's provider hint alongside the status dot.
const activeIdentifierStyle = computed(() => (activeProvider.value as any)?.identifier_style || "");
const activeIdentifierHint = computed(() => (activeProvider.value as any)?.identifier_hint || "");

async function handleSetActive(routeId: string) {
  if (!model.value || routeId === model.value.active_route_id) return;
  try {
    await setActiveRoute(model.value.id, routeId);
    toast.success(t("connections.model.toast.activeRouteUpdated"));
  } catch {
    toast.error(t("connections.model.toast.activeRouteFailed"));
  }
}

async function handleRemoveRoute(routeId: string) {
  if (!model.value) return;
  try {
    await deleteRoute(model.value.id, routeId);
    toast.success(t("connections.model.toast.routeRemoved"));
  } catch {
    toast.error(t("connections.model.toast.routeRemoveFailed"));
  }
}

// ── Add-route form (provider gated by the model's family) ──
const newRouteProviderId = ref("");
const newRouteIdentifier = ref("");

// Only providers the family supports AND the model doesn't already route through
// — a model has at most one route per provider.
const routeProviderItems = computed(() => {
  const usedProviderIds = new Set(routes.value.map((r) => r.provider_id));
  return providersForFamily(settingsStore.providers as any, selectedFamily.value as any)
    .filter((p: any) => !usedProviderIds.has(p.id))
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id }));
});
// Every supported provider already has a route → nothing left to add.
const allProvidersRouted = computed(
  () => !!form.model_family_id && routes.value.length > 0 && routeProviderItems.value.length === 0,
);
const newRouteProviderName = computed(
  () => providerName(newRouteProviderId.value) || t("connections.model.selectProvider"),
);
const newRouteHint = computed(() => identifierHintFor(newRouteProviderId.value));
const canAddRoute = computed(() => !!newRouteProviderId.value && !!newRouteIdentifier.value.trim());

// Drop a chosen provider the (possibly just-changed) family can no longer serve.
watch(
  () => form.model_family_id,
  () => {
    if (
      newRouteProviderId.value &&
      !routeProviderItems.value.some((i) => i.value === newRouteProviderId.value)
    ) {
      newRouteProviderId.value = "";
    }
  },
);

async function handleAddRoute() {
  if (!model.value || !canAddRoute.value) return;
  try {
    await addRoute(model.value.id, {
      provider_id: newRouteProviderId.value,
      model_identifier: newRouteIdentifier.value.trim(),
    });
    newRouteProviderId.value = "";
    newRouteIdentifier.value = "";
    toast.success(t("connections.model.toast.routeAdded"));
  } catch {
    toast.error(t("connections.model.toast.routeAddFailed"));
  }
}

async function handleSave() {
  if (!model.value) return;
  const updates: Record<string, unknown> = {};
  if (form.display_name !== model.value.display_name) updates.display_name = form.display_name;
  if (form.model_family_id !== model.value.model_family_id)
    updates.model_family_id = form.model_family_id;
  if (form.enabled !== model.value.enabled) updates.enabled = form.enabled;
  if (JSON.stringify(form.parameters) !== JSON.stringify(model.value.parameters ?? {}))
    updates.parameters = form.parameters;

  if (Object.keys(updates).length === 0) {
    toast.info(t("connections.model.toast.noChanges"));
    return;
  }

  try {
    const id = model.value.id;
    await saveModel(id, updates);
    // Re-fetch the full detail so the embedded model_family (and its parameter
    // schema) reflect any family change — the PUT response omits it.
    await fetchModel(id);
    toast.success(t("connections.model.toast.updated"));
  } catch (e) {
    toast.error(t("connections.model.toast.saveFailed"));
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
    toast.success(t("connections.model.toast.deleted"));
    router.push({ path: "/connections", query: { tab: "models" } });
  } catch (e) {
    toast.error(t("connections.model.toast.deleteFailed"));
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
              {{ $t("connections.model.editTitle") }}
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
                {{ $t("connections.model.identity") }}
              </h2>
              <div class="space-y-4">
                <!-- Display name -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                  >
                    {{ $t("connections.model.name") }}
                  </span>
                  <input
                    v-model="form.display_name"
                    type="text"
                    :placeholder="$t('connections.model.namePlaceholder')"
                    class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Original identifier (provider-independent identity, derived) -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                  >
                    {{ $t("connections.model.originalIdentifier") }}
                  </span>
                  <input
                    :value="model.original_identifier"
                    type="text"
                    readonly
                    class="h-11 w-full cursor-not-allowed rounded-lg border bg-base-300/20 px-4 font-mono text-sm text-muted-foreground outline-none"
                  />
                  <p class="mt-1.5 text-xs text-muted-foreground/70">
                    {{ $t("connections.model.originalIdentifierHint") }}
                  </p>
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
              </div>
            </div>

            <!-- Routes card -->
            <div class="rounded-xl border bg-base-200/50 p-5">
              <h2
                class="mb-1 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                {{ $t("connections.model.routes") }}
              </h2>
              <p class="mb-4 text-xs text-muted-foreground/70">
                {{ $t("connections.model.routesHint") }}
              </p>

              <!-- Empty -->
              <p
                v-if="routes.length === 0"
                class="rounded-lg border border-dashed bg-base-300/20 px-4 py-6 text-center text-sm text-muted-foreground"
              >
                {{ $t("connections.model.noRoutes") }}
              </p>

              <!-- Route list: the checked radio is the active "Route via" target -->
              <fieldset v-else class="space-y-2">
                <legend class="sr-only">{{ $t("connections.model.routeVia") }}</legend>
                <div
                  v-for="r in routes"
                  :key="r.id"
                  class="flex items-center gap-3 rounded-lg border bg-base-300/40 px-3 py-2.5"
                  :class="r.id === activeRouteId ? 'border-primary/50' : ''"
                >
                  <input
                    type="radio"
                    name="active-route"
                    class="radio radio-sm radio-primary shrink-0"
                    :checked="r.id === activeRouteId"
                    :aria-label="$t('connections.model.routeVia')"
                    @change="handleSetActive(r.id)"
                  />
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-foreground">{{
                        providerName(r.provider_id)
                      }}</span>
                      <span
                        v-if="r.id === activeRouteId"
                        class="rounded-full bg-primary/10 px-1.5 py-0.5 text-[0.625rem] font-medium text-primary"
                      >
                        {{ $t("connections.model.activeRoute") }}
                      </span>
                    </div>
                    <AppTooltip :text="identifierHintFor(r.provider_id)" side="top">
                      <span class="truncate font-mono text-xs text-muted-foreground">{{
                        r.model_identifier
                      }}</span>
                    </AppTooltip>
                  </div>
                  <button
                    class="flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-error/10 hover:text-error disabled:pointer-events-none disabled:opacity-40"
                    :disabled="saving || routes.length === 1"
                    :aria-label="$t('connections.model.removeRoute')"
                    @click="handleRemoveRoute(r.id)"
                  >
                    <AppIcon name="i-lucide-trash-2" class="size-3.5" />
                  </button>
                </div>
              </fieldset>

              <!-- Add route -->
              <div class="mt-4 border-t border-border/50 pt-4">
                <span
                  class="mb-2 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.model.addRoute") }}
                </span>
                <!-- Every supported provider already has a route — nothing to add. -->
                <p
                  v-if="allProvidersRouted"
                  class="rounded-lg border border-dashed bg-base-300/20 px-4 py-3 text-center text-xs text-muted-foreground"
                >
                  {{ $t("connections.model.allProvidersRouted") }}
                </p>
                <template v-else>
                  <div class="flex flex-col gap-2 sm:flex-row">
                    <SelectMenu
                      v-model="newRouteProviderId"
                      :items="routeProviderItems"
                      value-key="value"
                      :search-input="false"
                      class="sm:w-48"
                      :disabled="!form.model_family_id"
                    >
                      <button
                        class="flex h-10 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground outline-none disabled:cursor-not-allowed disabled:opacity-50"
                        :disabled="!form.model_family_id"
                      >
                        <span class="truncate">{{ newRouteProviderName }}</span>
                        <AppIcon
                          name="i-lucide-chevron-down"
                          class="size-4 shrink-0 text-muted-foreground"
                        />
                      </button>
                    </SelectMenu>
                    <input
                      v-model="newRouteIdentifier"
                      type="text"
                      placeholder="e.g. deepseek/deepseek-v4-pro"
                      class="h-10 min-w-0 flex-1 rounded-lg border bg-base-300/40 px-3 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                      @keydown.enter="handleAddRoute"
                    />
                    <button
                      class="flex h-10 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-primary px-4 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
                      :disabled="saving || !canAddRoute"
                      @click="handleAddRoute"
                    >
                      <AppIcon name="i-lucide-plus" class="size-4" />
                      {{ $t("connections.model.addRoute") }}
                    </button>
                  </div>
                  <p v-if="newRouteHint" class="mt-1.5 text-xs text-muted-foreground/70">
                    {{ newRouteHint }}
                  </p>
                </template>
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

                <!-- Active route provider status -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">{{
                    $t("connections.model.routeVia")
                  }}</span>
                  <div class="flex items-center gap-1.5">
                    <span class="text-sm text-foreground">{{ activeProviderName }}</span>
                    <span
                      class="size-2 rounded-full"
                      :class="model.provider_enabled ? 'bg-emerald-500' : 'bg-red-500'"
                    />
                  </div>
                </div>

                <!-- Identifier naming scheme (depends on the active route's provider) -->
                <div v-if="activeIdentifierStyle" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">{{
                    $t("connections.model.identifierFormat")
                  }}</span>
                  <AppTooltip :text="activeIdentifierHint" side="left">
                    <span
                      class="rounded-md border bg-base-300/40 px-2 py-0.5 font-mono text-xs text-foreground"
                    >
                      {{ activeIdentifierStyle }}
                    </span>
                  </AppTooltip>
                </div>

                <!-- Timestamps -->
                <div class="border-t border-border/50 pt-3">
                  <div class="space-y-1.5 text-[0.6875rem] text-muted-foreground/60">
                    <div class="flex justify-between">
                      <span>{{ $t("connections.model.created") }}</span>
                      <span>{{ formatDate(model.created_at) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>{{ $t("connections.model.updated") }}</span>
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
