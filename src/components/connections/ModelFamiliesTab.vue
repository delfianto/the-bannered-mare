<script setup lang="ts">
import { useModelFamilies } from "@/composables/useModelFamilies";

const { families, loading, error, page, totalPages, hasMore, loadPage } = useModelFamilies();

function goToPage(pageNum: number) {
  if (pageNum < 1 || pageNum > totalPages.value) return;
  loadPage(pageNum);
}

function parameterCount(family: (typeof families.value)[number]): string {
  // ModelFamilyListResponse doesn't include parameters, so we show provider_types count
  return `${family.provider_types.length} provider type${family.provider_types.length !== 1 ? "s" : ""}`;
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
    </div>

    <!-- Grid -->
    <div v-else>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div
          v-for="(family, index) in families"
          :key="family.id"
          class="animate-fade-in-up rounded-xl border border-[var(--border)] bg-card/50 p-5 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
          :style="{ animationDelay: `${index * 60}ms` }"
        >
          <!-- Header -->
          <div class="mb-2 flex items-start justify-between">
            <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ family.name }}
            </h3>
            <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <UIcon name="i-lucide-layers" class="h-3.5 w-3.5" />
              <span>{{ parameterCount(family) }}</span>
            </div>
          </div>

          <!-- Identifier -->
          <code class="mb-2 block text-xs text-muted-foreground">
            {{ family.family_identifier }}
          </code>

          <!-- Description -->
          <p
            v-if="family.description"
            class="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
          >
            {{ family.description }}
          </p>

          <!-- Provider type badges -->
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="pt in family.provider_types"
              :key="pt"
              class="rounded-full bg-accent px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-foreground"
            >
              {{ pt }}
            </span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="families.length === 0" class="flex flex-col items-center justify-center gap-2 py-12">
        <UIcon name="i-lucide-folder-open" class="h-8 w-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">No model families found</p>
      </div>

      <!-- Pagination -->
      <div v-if="families.length > 0" class="mt-4 flex items-center justify-between">
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
