<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { usePromptFragments } from "@/composables/usePromptFragments";
import DataTable, { type DataTableColumn } from "@/components/shared/DataTable.vue";

const router = useRouter();
const {
  fragments,
  loading,
  error,
  page,
  total,
  totalPages,
  loadPage,
  filterByUnusedOnly,
  refresh,
} = usePromptFragments({ pageSize: 20 });

const unusedOnly = ref(false);

function toggleUnusedOnly() {
  unusedOnly.value = !unusedOnly.value;
  filterByUnusedOnly(unusedOnly.value);
}

function typeBadgeClass(type: string): string {
  switch (type) {
    case "nsfw":
      return "bg-red-500/15 text-red-400";
    case "instruction":
      return "bg-blue-500/15 text-blue-400";
    case "system":
      return "bg-purple-500/15 text-purple-400";
    case "jailbreak":
      return "bg-orange-500/15 text-orange-400";
    default:
      return "bg-base-300 text-foreground";
  }
}

type FragmentRow = (typeof fragments.value)[number];
function openFragment(row: FragmentRow) {
  router.push(`/settings/fragments/${row.id}`);
}

const columns: DataTableColumn[] = [
  { key: "name", label: "Name", tdClass: "max-w-70 truncate font-medium text-foreground" },
  { key: "type", label: "Type" },
  { key: "scope", label: "Scope" },
  { key: "usedBy", label: "Used By" },
  { key: "updated", label: "Updated", tdClass: "text-xs text-muted-foreground" },
];
</script>

<template>
  <div>
    <!-- Primary action lives on the tab bar (see ProfilesTabs) -->
    <Teleport defer to="#loadout-tab-action">
      <RouterLink
        to="/settings/fragments/create"
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("connections.newFragment") }}
      </RouterLink>
    </Teleport>

    <!-- Filter bar -->
    <div class="mb-4 flex items-center justify-between">
      <button
        class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
        :class="
          unusedOnly
            ? 'border-warning/40 bg-warning/10 text-warning'
            : 'text-muted-foreground hover:bg-base-300'
        "
        @click="toggleUnusedOnly"
      >
        <AppIcon name="i-lucide-filter" class="size-3.5" />
        Unused only
      </button>
      <span class="text-xs text-muted-foreground"
        >{{ total }} fragment{{ total === 1 ? "" : "s" }}</span
      >
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="refresh"
      >
        {{ $t("common.retry") }}
      </button>
    </div>

    <!-- Empty -->
    <div
      v-else-if="fragments.length === 0"
      class="flex flex-col items-center justify-center gap-3 py-20"
    >
      <AppIcon name="i-lucide-puzzle" class="size-8 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">
        {{ unusedOnly ? "No unused fragments." : "No fragments yet." }}
      </p>
    </div>

    <!-- Table -->
    <DataTable
      v-else
      :columns="columns"
      :rows="fragments"
      :page="page"
      :total-pages="totalPages"
      @row-click="openFragment"
      @update:page="loadPage"
    >
      <template #cell-type="{ row }">
        <span
          class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
          :class="typeBadgeClass(row.fragment_type)"
        >
          {{ row.fragment_type }}
        </span>
      </template>
      <template #cell-scope="{ row }">
        <span v-if="row.is_global" class="text-success">Global</span>
        <span v-else class="text-muted-foreground">Local</span>
      </template>
      <template #cell-usedBy="{ row }">
        <span
          v-if="(row.used_by ?? []).length === 0"
          class="inline-flex items-center gap-1 rounded-full bg-warning/10 px-2 py-0.5 text-[0.6875rem] font-medium text-warning"
        >
          Unused
        </span>
        <span
          v-else
          class="text-xs text-muted-foreground"
          :title="(row.used_by ?? []).map((tpl) => tpl.name).join(', ')"
        >
          {{ (row.used_by ?? []).length }} template{{ (row.used_by ?? []).length === 1 ? "" : "s" }}
        </span>
      </template>
      <template #cell-updated="{ row }">
        {{ new Date(row.updated_at).toLocaleDateString() }}
      </template>
    </DataTable>
  </div>
</template>
