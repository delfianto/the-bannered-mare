<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useModels } from "@/composables/useModels";

const router = useRouter();

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

    <!-- Cards -->
    <div v-else>
      <!-- Empty -->
      <div v-if="models.length === 0" class="flex flex-col items-center justify-center gap-2 py-16">
        <UIcon name="i-lucide-search-x" class="h-8 w-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">No models found</p>
      </div>

      <!-- Card Grid -->
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="(model, index) in models"
          :key="model.id"
          class="group animate-fade-in-up cursor-pointer rounded-xl border border-[var(--border)] bg-card/50 p-4 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
          :style="{ animationDelay: `${index * 30}ms` }"
          @click="router.push(`/settings/models/${model.id}`)"
        >
          <!-- Header: name + status -->
          <div class="mb-2 flex items-start justify-between gap-2">
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

          <!-- Badges -->
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground">
              {{ model.provider_id }}
            </span>
            <span class="rounded-full bg-muted px-2 py-0.5 text-[9px] font-medium text-muted-foreground">
              {{ model.model_family_id }}
            </span>
          </div>

          <!-- Edit hint on hover -->
          <div class="mt-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
            <UIcon name="i-lucide-pencil" class="h-3 w-3" />
            Click to edit
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="mt-5 flex items-center justify-between">
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
