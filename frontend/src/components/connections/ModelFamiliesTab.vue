<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { useModelFamily } from "@/composables/useModelFamily";
import { useProviders } from "@/composables/useProviders";
import { useAppToast } from "@/composables/useToast";
import { useQueryState } from "@/composables/useQueryState";
import type { components } from "@/api/schema";
import Modal from "@/components/shared/Modal.vue";
import ModelFamilyForm from "./ModelFamilyForm.vue";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const router = useRouter();
const { readQuery, patchQuery } = useQueryState();

// Restore filters/page from the URL so they survive a detail-view round-trip.
const initialSearch = readQuery("q") ?? "";
const initialProviderType = readQuery("ptype") ?? "all";
const initialPage = Math.max(1, Number.parseInt(readQuery("page") ?? "1", 10) || 1);

const { families, loading, error, page, totalPages, loadPage, search, filterByProviderType } =
  useModelFamilies({
    initialPage,
    initialFilters: {
      name: initialSearch || undefined,
      provider_type: initialProviderType === "all" ? undefined : initialProviderType,
    },
  });
const { createFamily, saving } = useModelFamily();
const { providers } = useProviders();
const toast = useAppToast();
const { t } = useI18n();

const showCreate = ref(false);

async function onCreate(payload: components["schemas"]["ModelFamilyCreate"]) {
  try {
    await createFamily(payload);
    toast.success(t("connections.family.toast.created"));
    showCreate.value = false;
    await loadPage(1);
    patchQuery({ page: undefined });
  } catch {
    toast.error(t("connections.family.toast.createFailed"));
  }
}

const searchQuery = ref(initialSearch);
const searchFocused = ref(false);
const selectedProviderType = ref(initialProviderType);

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
function handleSearch(value: string) {
  searchQuery.value = value;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    search(value);
    patchQuery({ q: value || undefined, page: undefined });
  }, 300);
}

// Families reference provider *types* (e.g. "openai"). List the distinct types
// across configured providers, but label each with the provider's friendly name
// (matching the Models tab) while keeping the type as the filter value.
const providerTypeItems = computed(() => {
  const nameByType = new Map<string, string>();
  for (const p of providers.value) {
    if (!nameByType.has(p.provider_type)) nameByType.set(p.provider_type, p.name);
  }
  return [
    { label: "All providers", value: "all" },
    ...[...nameByType.entries()]
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([type, name]) => ({ label: name, value: type })),
  ];
});

const providerTypeLabel = computed(
  () =>
    providerTypeItems.value.find((i) => i.value === selectedProviderType.value)?.label ??
    "All providers",
);

function handleProviderTypeFilter(value: string) {
  selectedProviderType.value = value;
  filterByProviderType(value === "all" ? undefined : value);
  patchQuery({ ptype: value === "all" ? undefined : value, page: undefined });
}

function goToPage(p: number) {
  loadPage(p);
  patchQuery({ page: p > 1 ? p : undefined });
}

const columns: DataTableColumn[] = [
  { key: "name", label: "Name", tdClass: "max-w-55 truncate font-medium text-foreground" },
  {
    key: "family_identifier",
    label: "Identifier",
    tdClass: "max-w-50 truncate font-mono text-xs text-muted-foreground",
  },
  {
    key: "description",
    label: "Description",
    tdClass: "max-w-80 truncate text-xs text-muted-foreground",
  },
  { key: "providers", label: "Providers" },
];

type FamilyRow = (typeof families.value)[number];
function openFamily(row: FamilyRow) {
  router.push(`/settings/model-families/${row.id}`);
}
</script>

<template>
  <div>
    <!-- Primary action lives on the tab bar (see ConnectionsTabs) -->
    <Teleport defer to="#connections-tab-action">
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="showCreate = true"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("connections.newFamily") }}
      </button>
    </Teleport>

    <!-- Create modal -->
    <Modal
      :show="showCreate"
      :title="$t('connections.newFamily')"
      max-width="lg"
      @close="showCreate = false"
    >
      <ModelFamilyForm :saving="saving" @submit="onCreate" @cancel="showCreate = false" />
    </Modal>

    <!-- Filters row -->
    <div class="mb-4 flex flex-wrap items-center gap-2">
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
            placeholder="Search families…"
            aria-label="Search model families"
            autocomplete="off"
            class="h-9 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            @input="handleSearch(($event.target as HTMLInputElement).value)"
            @focus="searchFocused = true"
            @blur="searchFocused = false"
          />
        </div>
      </div>

      <!-- Provider-type filter (server-side via API) -->
      <SelectMenu
        :model-value="selectedProviderType"
        :items="providerTypeItems"
        value-key="value"
        :search-input="false"
        @update:model-value="handleProviderTypeFilter"
      >
        <button
          class="flex h-9 min-w-40 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <AppIcon name="i-lucide-server" class="size-3.5" />
          {{ providerTypeLabel }}
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
        v-if="families.length === 0"
        class="flex flex-col items-center justify-center gap-2 py-16"
      >
        <AppIcon name="i-lucide-folder-open" class="size-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">{{ $t("connections.noFamilies") }}</p>
      </div>

      <!-- Table -->
      <DataTable
        v-else
        :columns="columns"
        :rows="families"
        :page="page"
        :total-pages="totalPages"
        @row-click="openFamily"
        @update:page="goToPage"
      >
        <template #cell-description="{ row }">{{ row.description || "—" }}</template>
        <template #cell-providers="{ row }">
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              v-for="pt in row.provider_types.slice(0, 4)"
              :key="pt"
              class="rounded-full bg-base-300 px-2 py-0.5 text-4xs font-medium tracking-wide text-foreground uppercase"
            >
              {{ pt }}
            </span>
            <span v-if="row.provider_types.length > 4" class="text-3xs text-muted-foreground">
              +{{ row.provider_types.length - 4 }}
            </span>
          </div>
        </template>
      </DataTable>
    </div>
  </div>
</template>
