<script lang="ts">
export interface DataTableColumn {
  /** Row property to render by default, and the slot name suffix: `cell-<key>`. */
  key: string;
  label: string;
  /** Extra classes for this column's <td>. */
  tdClass?: string;
  /** Extra classes for this column's <th>. */
  thClass?: string;
}
</script>

<script setup lang="ts" generic="T extends Record<string, unknown>">
import AppPagination from "@/components/shared/AppPagination.vue";

withDefaults(
  defineProps<{
    columns: DataTableColumn[];
    rows: readonly T[];
    rowKey?: string;
    page?: number;
    totalPages?: number;
  }>(),
  {
    rowKey: "id",
    page: 1,
    totalPages: 1,
  },
);

const emit = defineEmits<{
  rowClick: [row: T];
  "update:page": [page: number];
}>();
</script>

<template>
  <div>
    <div class="overflow-hidden rounded-xl border bg-base-200/50">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="border-b bg-base-300/30">
            <th
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-2.5 font-story text-3xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              :class="col.thClass"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="String(row[rowKey])"
            class="cursor-pointer border-b border-border/50 transition-colors last:border-0 hover:bg-base-300/40"
            @click="emit('rowClick', row)"
          >
            <td v-for="col in columns" :key="col.key" class="px-4 py-2.5" :class="col.tdClass">
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppPagination
      v-if="totalPages > 1"
      :page="page"
      :total-pages="totalPages"
      class="mt-5"
      @update:page="emit('update:page', $event)"
    />
  </div>
</template>
