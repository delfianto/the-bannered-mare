<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { usePromptFragments } from "@/composables/usePromptFragments";

const router = useRouter();
const {
  fragments,
  loading,
  error,
  page,
  hasMore,
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
      return "bg-accent text-foreground";
  }
}

function openFragment(id: string) {
  router.push(`/settings/fragments/${id}`);
}
</script>

<template>
  <div>
    <!-- Filter bar -->
    <div class="mb-4 flex items-center justify-between">
      <button
        class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
        :class="
          unusedOnly
            ? 'border-amber-500/40 bg-amber-500/10 text-amber-500'
            : 'text-muted-foreground hover:bg-accent'
        "
        @click="toggleUnusedOnly"
      >
        <UIcon name="i-lucide-filter" class="h-3.5 w-3.5" />
        Unused only
      </button>
      <span class="text-xs text-muted-foreground"
        >{{ total }} fragment{{ total === 1 ? "" : "s" }}</span
      >
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
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
      <UIcon name="i-lucide-puzzle" class="h-8 w-8 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">
        {{ unusedOnly ? "No unused fragments." : "No fragments yet." }}
      </p>
    </div>

    <!-- Table -->
    <div v-else class="overflow-hidden rounded-xl border bg-card/50">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="border-b bg-muted/30">
            <th
              class="px-4 py-2.5 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Name
            </th>
            <th
              class="px-4 py-2.5 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Type
            </th>
            <th
              class="px-4 py-2.5 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Scope
            </th>
            <th
              class="px-4 py-2.5 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Used By
            </th>
            <th
              class="px-4 py-2.5 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Updated
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="fragment in fragments"
            :key="fragment.id"
            class="cursor-pointer border-b border-border/50 transition-colors last:border-0 hover:bg-accent/40"
            @click="openFragment(fragment.id)"
          >
            <td class="max-w-[280px] truncate px-4 py-2.5 font-medium text-foreground">
              {{ fragment.name }}
            </td>
            <td class="px-4 py-2.5">
              <span
                class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
                :class="typeBadgeClass(fragment.fragment_type)"
              >
                {{ fragment.fragment_type }}
              </span>
            </td>
            <td class="px-4 py-2.5">
              <span v-if="fragment.is_global" class="text-emerald-500">Global</span>
              <span v-else class="text-muted-foreground">Local</span>
            </td>
            <td class="px-4 py-2.5">
              <span
                v-if="(fragment.used_by ?? []).length === 0"
                class="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-500"
              >
                Unused
              </span>
              <span
                v-else
                class="text-xs text-muted-foreground"
                :title="(fragment.used_by ?? []).map((t) => t.name).join(', ')"
              >
                {{ (fragment.used_by ?? []).length }} template{{
                  (fragment.used_by ?? []).length === 1 ? "" : "s"
                }}
              </span>
            </td>
            <td class="px-4 py-2.5 text-xs text-muted-foreground">
              {{ new Date(fragment.updated_at).toLocaleDateString() }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="mt-5 flex items-center justify-between">
      <span class="text-xs text-muted-foreground">Page {{ page }} of {{ totalPages }}</span>
      <div class="flex items-center gap-2">
        <UButton variant="outline" size="xs" :disabled="page <= 1" @click="loadPage(page - 1)">
          <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5" />
          Prev
        </UButton>
        <UButton variant="outline" size="xs" :disabled="!hasMore" @click="loadPage(page + 1)">
          Next
          <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5" />
        </UButton>
      </div>
    </div>
  </div>
</template>
