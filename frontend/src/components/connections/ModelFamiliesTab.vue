<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useModelFamilies } from "@/composables/useModelFamilies";
import { useProviders } from "@/composables/useProviders";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const router = useRouter();
const { families, loading, error, page, totalPages, loadPage, search, filterByProviderType } =
  useModelFamilies();
const { providers } = useProviders();

const searchQuery = ref("");
const searchFocused = ref(false);
const selectedProviderType = ref("all");

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
function handleSearch(value: string) {
  searchQuery.value = value;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => search(value), 300);
}

// Families reference provider *types* (e.g. "openai"). List the distinct types
// across configured providers, but label each with the provider's friendly name
// (matching the Models tab) while keeping the type as the filter value.
const providerTypeItems = computed(() => {
  const nameByType = new Map<string, string>();
  for (const p of providers.value as any[]) {
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
}

const columns: DataTableColumn[] = [
  { key: "name", label: "Name", tdClass: "max-w-[220px] truncate font-medium text-foreground" },
  {
    key: "family_identifier",
    label: "Identifier",
    tdClass: "max-w-[200px] truncate font-mono text-xs text-muted-foreground",
  },
  {
    key: "description",
    label: "Description",
    tdClass: "max-w-[320px] truncate text-xs text-muted-foreground",
  },
  { key: "providers", label: "Providers" },
];

function openFamily(row: any) {
  router.push(`/settings/model-families/${row.id}`);
}
</script>

<template>
  <div>
    <!-- Filters row -->
    <div class="mb-4 flex flex-wrap items-center gap-2">
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
      <USelectMenu
        :model-value="selectedProviderType"
        :items="providerTypeItems"
        value-key="value"
        :search-input="false"
        :ui="{
          base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
          content: 'border bg-card ring-0 outline-none shadow-lg',
          item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
        }"
        @update:model-value="handleProviderTypeFilter"
      >
        <button
          class="flex h-9 min-w-[160px] items-center gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
        >
          <UIcon name="i-lucide-server" class="size-3.5" />
          {{ providerTypeLabel }}
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
        v-if="families.length === 0"
        class="flex flex-col items-center justify-center gap-2 py-16"
      >
        <UIcon name="i-lucide-folder-open" class="size-8 text-muted-foreground/50" />
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
        @update:page="loadPage"
      >
        <template #cell-description="{ row }">{{ row.description || "—" }}</template>
        <template #cell-providers="{ row }">
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              v-for="pt in row.provider_types.slice(0, 4)"
              :key="pt"
              class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium tracking-wide text-foreground uppercase"
            >
              {{ pt }}
            </span>
            <span v-if="row.provider_types.length > 4" class="text-[10px] text-muted-foreground">
              +{{ row.provider_types.length - 4 }}
            </span>
          </div>
        </template>
      </DataTable>
    </div>
  </div>
</template>
