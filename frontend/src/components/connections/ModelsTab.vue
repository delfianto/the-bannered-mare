<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useModels } from "@/composables/useModels";
import { useModel } from "@/composables/useModel";
import { useProviders } from "@/composables/useProviders";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { useAppToast } from "@/composables/useToast";
import { useQueryState } from "@/composables/useQueryState";
import ModelCreateModal from "./ModelCreateModal.vue";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const { t } = useI18n();
const router = useRouter();
const { toggleFlags } = useModel();
const toast = useAppToast();
const { readQuery, patchQuery } = useQueryState();

// Restore filters/page from the URL so they survive a detail-view round-trip.
const initialSearch = readQuery("q") ?? "";
const initialProvider = readQuery("provider") ?? "all";
const initialFamily = readQuery("family") ?? "all";
const rawStatus = readQuery("status");
const initialStatus: "all" | "enabled" | "disabled" =
  rawStatus === "enabled" || rawStatus === "disabled" ? rawStatus : "all";
const initialPage = Math.max(1, Number.parseInt(readQuery("page") ?? "1", 10) || 1);

const {
  models,
  loading,
  error,
  page,
  totalPages,
  loadPage,
  search,
  filterByProvider,
  filterByFamily,
  filterByStatus,
} = useModels({
  initialPage,
  initialFilters: {
    name: initialSearch || undefined,
    provider_id: initialProvider === "all" ? undefined : initialProvider,
    model_family_id: initialFamily === "all" ? undefined : initialFamily,
    enabled: initialStatus === "all" ? undefined : initialStatus === "enabled",
  },
});
const { providers } = useProviders();
const { families } = useModelFamilies({ pageSize: 100 });

// ── Create modal ─────────────────────────────────────────
const showCreate = ref(false);

function openCreate() {
  showCreate.value = true;
}

function onCreated() {
  loadPage(1);
  patchQuery({ page: undefined });
}

const searchQuery = ref(initialSearch);
const searchFocused = ref(false);
const selectedProvider = ref(initialProvider);
const selectedFamily = ref(initialFamily);
const selectedStatus = ref<"all" | "enabled" | "disabled">(initialStatus);

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// Each filter change resets to page 1 (the composable does the reload) and is
// mirrored into the URL query so browser back/forward restores it.
function handleSearch(value: string) {
  searchQuery.value = value;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    search(value);
    patchQuery({ q: value || undefined, page: undefined });
  }, 300);
}

function handleProviderFilter(value: string) {
  selectedProvider.value = value;
  filterByProvider(value === "all" ? undefined : value);
  patchQuery({ provider: value === "all" ? undefined : value, page: undefined });
}

function handleFamilyFilter(value: string) {
  selectedFamily.value = value;
  filterByFamily(value === "all" ? undefined : value);
  patchQuery({ family: value === "all" ? undefined : value, page: undefined });
}

function handleStatusFilter(value: string) {
  selectedStatus.value = value as "all" | "enabled" | "disabled";
  filterByStatus(value === "all" ? undefined : value === "enabled");
  patchQuery({ status: value === "all" ? undefined : value, page: undefined });
}

function goToPage(p: number) {
  loadPage(p);
  patchQuery({ page: p > 1 ? p : undefined });
}

const providerItems = computed(() => [
  { label: t("connections.allProviders"), value: "all" },
  ...[...providers.value]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
]);

const familyItems = computed(() => [
  { label: t("connections.allFamilies"), value: "all" },
  ...families.value.map((f) => ({ label: f.name, value: f.id })),
]);

const providerLabel = computed(
  () =>
    providerItems.value.find((i) => i.value === selectedProvider.value)?.label ??
    t("connections.allProviders"),
);

const familyLabel = computed(
  () =>
    familyItems.value.find((i) => i.value === selectedFamily.value)?.label ??
    t("connections.allFamilies"),
);

const statusItems = computed(() => [
  { label: t("connections.allStatuses"), value: "all" },
  { label: t("connections.statusEnabled"), value: "enabled" },
  { label: t("connections.statusDisabled"), value: "disabled" },
]);

const statusLabel = computed(
  () =>
    statusItems.value.find((i) => i.value === selectedStatus.value)?.label ??
    t("connections.allStatuses"),
);

const filteredModels = computed(() => models.value);

// Resolve the raw FK ids to human names (both lists are already loaded above).
function providerNameFor(id: string): string {
  return providers.value.find((p) => p.id === id)?.name ?? id;
}
function familyNameFor(id: string): string {
  return families.value.find((f) => f.id === id)?.name ?? id;
}

const columns: DataTableColumn[] = [
  {
    key: "display_name",
    label: t("connections.model.name"),
    tdClass: "max-w-60 truncate font-medium text-foreground",
  },
  { key: "family", label: t("connections.model.family"), tdClass: "text-xs text-muted-foreground" },
  { key: "routes", label: t("connections.model.routes"), tdClass: "text-xs text-muted-foreground" },
  { key: "status", label: "Status" },
];

// The active route decides which provider a registry runs through; the row shows
// that provider's name plus a "+N" badge when the registry has fallback routes.
type ModelRow = (typeof models.value)[number];
function activeProviderName(row: ModelRow): string {
  const active = row.routes.find((r) => r.id === row.active_route_id) ?? row.routes[0];
  return active ? providerNameFor(active.provider_id) : t("connections.model.noRoutes");
}

function openModel(row: any) {
  router.push(`/settings/models/${row.id}`);
}

const togglingIds = ref<Set<string>>(new Set());

async function handleToggleEnabled(row: any) {
  if (togglingIds.value.has(row.id)) return;

  const previous = row.enabled;
  row.enabled = !previous;
  togglingIds.value.add(row.id);
  try {
    await toggleFlags(row.id, { enabled: row.enabled });
  } catch {
    row.enabled = previous;
    toast.error("Failed to update model");
  } finally {
    togglingIds.value.delete(row.id);
  }
}
</script>

<template>
  <div>
    <!-- Primary action lives on the tab bar (see ConnectionsTabs) -->
    <Teleport defer to="#connections-tab-action">
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="openCreate"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("connections.newModel") }}
      </button>
    </Teleport>

    <!-- Create modal -->
    <ModelCreateModal :show="showCreate" @close="showCreate = false" @created="onCreated" />

    <!-- Filters row -->
    <div class="mb-6 flex animate-fade-in-up flex-wrap items-center gap-2">
      <!-- Search -->
      <div class="relative min-w-50 flex-1">
        <div
          class="flex items-center gap-2 rounded-lg border px-3 transition-all duration-200"
          :class="
            searchFocused
              ? 'border-primary/40 bg-base-100 shadow-[0_0_0_3px_var(--color-primary)/0.08]'
              : 'border-border bg-base-300/40 hover:border-muted-foreground/30'
          "
        >
          <AppIcon
            name="i-lucide-search"
            class="size-4 shrink-0 transition-colors"
            :class="searchFocused ? 'text-primary' : 'text-muted-foreground'"
          />
          <input
            type="text"
            :value="searchQuery"
            :placeholder="t('connections.searchModels')"
            aria-label="Search models"
            autocomplete="off"
            class="h-9 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            @input="handleSearch(($event.target as HTMLInputElement).value)"
            @focus="searchFocused = true"
            @blur="searchFocused = false"
          />
        </div>
      </div>

      <!-- Provider filter (server-side via API) -->
      <SelectMenu
        :model-value="selectedProvider"
        :items="providerItems"
        value-key="value"
        :search-input="false"
        @update:model-value="handleProviderFilter"
      >
        <button
          class="flex h-9 min-w-40 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <AppIcon name="i-lucide-server" class="size-3.5" />
          {{ providerLabel }}
        </button>
      </SelectMenu>

      <!-- Family filter (server-side via API) -->
      <SelectMenu
        :model-value="selectedFamily"
        :items="familyItems"
        value-key="value"
        @update:model-value="handleFamilyFilter"
      >
        <button
          class="flex h-9 min-w-40 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <AppIcon name="i-lucide-layers" class="size-3.5" />
          {{ familyLabel }}
        </button>
      </SelectMenu>

      <!-- Status filter (enabled/disabled, server-side via API) -->
      <SelectMenu
        :model-value="selectedStatus"
        :items="statusItems"
        value-key="value"
        :search-input="false"
        @update:model-value="handleStatusFilter"
      >
        <button
          class="flex h-9 min-w-37.5 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <AppIcon name="i-lucide-toggle-left" class="size-3.5" />
          {{ statusLabel }}
        </button>
      </SelectMenu>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty -->
      <div
        v-if="filteredModels.length === 0"
        class="flex flex-col items-center justify-center gap-2 py-16"
      >
        <AppIcon name="i-lucide-search-x" class="size-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">{{ $t("connections.noModels") }}</p>
      </div>

      <!-- Table -->
      <DataTable
        v-else
        :columns="columns"
        :rows="filteredModels"
        :page="page"
        :total-pages="totalPages"
        @row-click="openModel"
        @update:page="goToPage"
      >
        <template #cell-family="{ row }">{{ familyNameFor(row.model_family_id) }}</template>
        <template #cell-routes="{ row }">
          <span class="inline-flex items-center gap-1.5">
            <span :class="row.routes.length === 0 ? 'text-muted-foreground/60 italic' : ''">
              {{ activeProviderName(row) }}
            </span>
            <span
              v-if="row.routes.length > 1"
              class="rounded-full bg-base-300 px-1.5 py-0.5 text-[0.625rem] font-medium text-muted-foreground"
            >
              +{{ row.routes.length - 1 }}
            </span>
          </span>
        </template>
        <template #cell-status="{ row }">
          <AppToggle
            :model-value="row.enabled"
            :disabled="togglingIds.has(row.id)"
            :aria-label="row.enabled ? 'Disable model' : 'Enable model'"
            @click.stop
            @change="handleToggleEnabled(row)"
          />
        </template>
      </DataTable>
    </div>
  </div>
</template>
