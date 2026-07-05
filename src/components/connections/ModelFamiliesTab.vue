<script setup lang="ts">
import { useRouter } from "vue-router";
import { useModelFamilies } from "@/composables/useModelFamilies";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const router = useRouter();
const { families, loading, error, page, totalPages, loadPage } = useModelFamilies();

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
