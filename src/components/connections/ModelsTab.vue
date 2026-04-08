<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useModels } from "@/composables/useModels";
import { useProviders } from "@/composables/useProviders";
import { useModelFamilies } from "@/composables/useModelFamilies";

const router = useRouter();

const { models, loading, error, page, hasMore, totalPages, loadPage, search, filterByProvider } = useModels();
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

const providerItems = computed(() => [
  { label: "All Providers", value: "all" },
  ...[...providers.value].sort((a: any, b: any) => a.name.localeCompare(b.name)).map((p: any) => ({ label: p.name, value: p.id })),
]);

const familyItems = computed(() => [
  { label: "All Families", value: "all" },
  ...families.value.map((f: any) => ({ label: f.name, value: f.id })),
]);

const providerLabel = computed(() =>
  providerItems.value.find((i) => i.value === selectedProvider.value)?.label ?? "All Providers",
);

// const familyLabel = computed(() =>
//   familyItems.value.find((i) => i.value === selectedFamily.value)?.label ?? "All Families",
// );

// TODO: Family filter — needs model_family_id param added to backend API
// TODO: Add order_by=name query param when backend supports it
const filteredModels = computed(() => models.value);
</script>

<template>
  <div>
    <!-- Filters row -->
    <div class="animate-fade-in-up mb-6 flex flex-wrap items-center gap-2">
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
            class="h-4 w-4 shrink-0 transition-colors"
            :class="searchFocused ? 'text-primary' : 'text-muted-foreground'"
          />
          <input
            type="text"
            :value="searchQuery"
            placeholder="Search models..."
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
        @update:model-value="handleProviderFilter"
        :items="providerItems"
        value-key="value"
        :search-input="false"
        :ui="{
          base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
          content: 'border border-border bg-card ring-0 outline-none shadow-lg',
          item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
        }"
      >
        <button
          class="flex h-9 min-w-[160px] items-center gap-1.5 rounded-lg border border-border bg-muted/40 px-3 text-sm text-muted-foreground outline-none transition-all hover:border-muted-foreground/30"
        >
          <UIcon name="i-lucide-server" class="h-3.5 w-3.5" />
          {{ providerLabel }}
        </button>
      </USelectMenu>

      <!-- TODO: Family filter — needs model_family_id query param added to backend API -->
      <USelectMenu
        v-model="selectedFamily"
        :items="familyItems"
        value-key="value"
        :search-input="false"
        disabled
        :ui="{
          base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
          content: 'border border-border bg-card ring-0 outline-none shadow-lg',
          item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
        }"
      >
        <button
          disabled
          class="flex h-9 min-w-[160px] items-center gap-1.5 rounded-lg border border-border bg-muted/40 px-3 text-sm text-muted-foreground/50 outline-none cursor-not-allowed"
        >
          <UIcon name="i-lucide-layers" class="h-3.5 w-3.5" />
          All Families
        </button>
      </USelectMenu>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
    </div>

    <!-- Cards -->
    <div v-else>
      <!-- Empty -->
      <div v-if="filteredModels.length === 0" class="flex flex-col items-center justify-center gap-2 py-16">
        <UIcon name="i-lucide-search-x" class="h-8 w-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">No models found</p>
      </div>

      <!-- Card Grid -->
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="(model, index) in filteredModels"
          :key="model.id"
          class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border border-border bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
          :style="{ animationDelay: `${index * 30}ms` }"
          @click="router.push(`/settings/models/${model.id}`)"
        >
          <!-- Header: name + status -->
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
                {{ model.name }}
              </h3>
              <p class="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                {{ model.model_identifier }}
              </p>
            </div>
            <span
              class="mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full"
              :class="model.enabled ? 'bg-emerald-500' : 'bg-red-400'"
              :title="model.enabled ? 'Enabled' : 'Disabled'"
            />
          </div>

          <!-- Spacer -->
          <div class="flex-1" />

          <!-- Badges (pinned to bottom) -->
          <div class="flex flex-wrap items-center gap-1.5 border-t border-border/30 pt-3">
            <span class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground">
              {{ model.provider_id }}
            </span>
            <span class="rounded-full bg-muted px-2 py-0.5 text-[9px] font-medium text-muted-foreground">
              {{ model.model_family_id }}
            </span>
          </div>

          <!-- Edit hint -->
          <div class="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
            <UIcon name="i-lucide-pencil" class="h-3 w-3" />
            Edit
          </div>
        </div>
      </div>

      <!-- Pagination (only if no local filters active and multiple pages) -->
      <div v-if="totalPages > 1 && selectedProvider === 'all' && selectedFamily === 'all'" class="mt-5 flex items-center justify-between">
        <span class="text-xs text-muted-foreground">
          Page {{ page }} of {{ totalPages }}
        </span>
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

      <!-- Result count when filtering -->
      <div v-if="selectedProvider !== 'all' || selectedFamily !== 'all'" class="mt-4">
        <span class="text-xs text-muted-foreground">
          {{ filteredModels.length }} of {{ models.length }} models
        </span>
      </div>
    </div>
  </div>
</template>
