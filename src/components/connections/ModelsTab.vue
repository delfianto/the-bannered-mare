<script setup lang="ts">
import { ref } from "vue";
import { useModels } from "@/composables/useModels";

const { models, loading, error, page, hasMore, totalPages, loadPage, search } = useModels();

const searchQuery = ref("");
const searchFocused = ref(false);

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function handleSearch(value: string) {
  searchQuery.value = value;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    search(value);
  }, 300);
}

function goToPage(pageNum: number) {
  if (pageNum < 1 || pageNum > totalPages.value) return;
  loadPage(pageNum, searchQuery.value || undefined);
}
</script>

<template>
  <div>
    <!-- Search -->
    <div class="animate-fade-in-up mb-6">
      <div class="relative max-w-md">
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

    <!-- Table -->
    <div v-else>
      <div class="animate-fade-in-up overflow-hidden rounded-xl border border-[var(--border)]">
        <!-- Header -->
        <div class="grid grid-cols-[1fr_140px_160px_80px] gap-4 border-b border-border bg-muted/30 px-5 py-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <span>Model</span>
          <span>Provider</span>
          <span>Family</span>
          <span class="text-center">Status</span>
        </div>

        <!-- Empty state -->
        <div v-if="models.length === 0" class="flex flex-col items-center justify-center gap-2 py-12">
          <UIcon name="i-lucide-search-x" class="h-8 w-8 text-muted-foreground/50" />
          <p class="text-sm text-muted-foreground">No models found</p>
        </div>

        <!-- Rows -->
        <div
          v-for="(model, index) in models"
          :key="model.id"
          class="grid grid-cols-[1fr_140px_160px_80px] items-center gap-4 border-b border-border/50 px-5 py-3 transition-colors last:border-b-0 hover:bg-accent/30"
          :style="{ animationDelay: `${index * 40}ms` }"
        >
          <!-- Model name -->
          <div class="min-w-0">
            <p class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ model.name }}
            </p>
            <p class="truncate text-xs text-muted-foreground">
              {{ model.model_identifier }}
            </p>
          </div>

          <!-- Provider -->
          <div>
            <span class="rounded-full bg-accent px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-foreground">
              {{ model.provider_id }}
            </span>
          </div>

          <!-- Family -->
          <div class="min-w-0">
            <p class="truncate text-xs text-muted-foreground">
              {{ model.model_family_id }}
            </p>
          </div>

          <!-- Enabled -->
          <div class="flex justify-center">
            <span
              class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
              :class="
                model.enabled
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-red-500/10 text-red-500'
              "
            >
              <span
                class="h-1.5 w-1.5 rounded-full"
                :class="model.enabled ? 'bg-emerald-500' : 'bg-red-500'"
              />
              {{ model.enabled ? "On" : "Off" }}
            </span>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div class="mt-4 flex items-center justify-between" style="animation-delay: 200ms">
        <span class="text-xs text-muted-foreground">
          Page {{ page }} of {{ totalPages }}
        </span>
        <div class="flex items-center gap-2">
          <UButton
            variant="outline"
            size="xs"
            :disabled="page <= 1"
            @click="goToPage(page - 1)"
          >
            <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5" />
            Prev
          </UButton>
          <UButton
            variant="outline"
            size="xs"
            :disabled="!hasMore"
            @click="goToPage(page + 1)"
          >
            Next
            <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5" />
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>
