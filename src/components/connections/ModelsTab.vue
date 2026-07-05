<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useModels } from "@/composables/useModels";
import { useProviders } from "@/composables/useProviders";
import { useModelFamilies } from "@/composables/useModelFamilies";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const { t } = useI18n();
const router = useRouter();

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
} = useModels();
const { providers } = useProviders();
const { families } = useModelFamilies({ pageSize: 100 });

const searchQuery = ref("");
const searchFocused = ref(false);
const selectedProvider = ref("all");
const selectedFamily = ref("all"); // TODO: enable when backend supports model_family_id filter

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function handleSearch(value: string) {
  searchQuery.value = value;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    search(value);
  }, 300);
}

function handleProviderFilter(value: string) {
  selectedProvider.value = value;
  filterByProvider(value === "all" ? undefined : value);
}

function handleFamilyFilter(value: string) {
  selectedFamily.value = value;
  filterByFamily(value === "all" ? undefined : value);
}

const providerItems = computed(() => [
  { label: t("connections.allProviders"), value: "all" },
  ...[...providers.value]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((p: any) => ({ label: p.name, value: p.id })),
]);

const familyItems = computed(() => [
  { label: t("connections.allFamilies"), value: "all" },
  ...families.value.map((f: any) => ({ label: f.name, value: f.id })),
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

const filteredModels = computed(() => models.value);

// Resolve the raw FK ids to human names (both lists are already loaded above).
function providerNameFor(id: string): string {
  return providers.value.find((p: any) => p.id === id)?.name ?? id;
}
function familyNameFor(id: string): string {
  return families.value.find((f: any) => f.id === id)?.name ?? id;
}

const columns: DataTableColumn[] = [
  { key: "name", label: "Name", tdClass: "max-w-[240px] truncate font-medium text-foreground" },
  {
    key: "model_identifier",
    label: "Identifier",
    tdClass: "max-w-[220px] truncate font-mono text-xs text-muted-foreground",
  },
  { key: "provider", label: "Provider", tdClass: "text-xs text-muted-foreground" },
  { key: "family", label: "Family", tdClass: "text-xs text-muted-foreground" },
  { key: "status", label: "Status" },
];

function openModel(row: any) {
  router.push(`/settings/models/${row.id}`);
}
</script>

<template>
  <div>
    <!-- Filters row -->
    <div class="mb-6 flex animate-fade-in-up flex-wrap items-center gap-2">
      <!-- Search -->
      <div class="relative min-w-[200px] flex-1">
        <div
          class="flex items-center gap-2 rounded-lg border px-3 transition-all duration-200"
          :class="
            searchFocused
              ? 'border-primary/40 bg-background shadow-[0_0_0_3px_var(--color-primary)/0.08]'
              : 'border-border bg-muted/40 hover:border-muted-foreground/30'
          "
        >
          <UIcon
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
      <USelectMenu
        :model-value="selectedProvider"
        :items="providerItems"
        value-key="value"
        :search-input="false"
        :ui="{
          base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
          content: 'border bg-card ring-0 outline-none shadow-lg',
          item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
        }"
        @update:model-value="handleProviderFilter"
      >
        <button
          class="flex h-9 min-w-[160px] items-center gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <UIcon name="i-lucide-server" class="size-3.5" />
          {{ providerLabel }}
        </button>
      </USelectMenu>

      <!-- Family filter (server-side via API) -->
      <USelectMenu
        :model-value="selectedFamily"
        :items="familyItems"
        value-key="value"
        :ui="{
          base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
          content: 'border bg-card ring-0 outline-none shadow-lg',
          item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
        }"
        @update:model-value="handleFamilyFilter"
      >
        <button
          class="flex h-9 min-w-[160px] items-center gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <UIcon name="i-lucide-layers" class="size-3.5" />
          {{ familyLabel }}
        </button>
      </USelectMenu>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="size-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty -->
      <div
        v-if="filteredModels.length === 0"
        class="flex flex-col items-center justify-center gap-2 py-16"
      >
        <UIcon name="i-lucide-search-x" class="size-8 text-muted-foreground/50" />
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
        @update:page="loadPage"
      >
        <template #cell-provider="{ row }">{{ providerNameFor(row.provider_id) }}</template>
        <template #cell-family="{ row }">{{ familyNameFor(row.model_family_id) }}</template>
        <template #cell-status="{ row }">
          <span
            v-if="row.enabled"
            class="inline-flex items-center gap-1.5 text-xs text-emerald-500"
          >
            <span class="size-1.5 rounded-full bg-emerald-500" />Enabled
          </span>
          <span v-else class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <span class="size-1.5 rounded-full bg-red-400" />Disabled
          </span>
        </template>
      </DataTable>
    </div>
  </div>
</template>
