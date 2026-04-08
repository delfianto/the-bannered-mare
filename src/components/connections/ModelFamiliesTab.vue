<script setup lang="ts">
import { useModelFamilies } from "@/composables/useModelFamilies";

const { families, loading, error, page, totalPages, hasMore, loadPage } = useModelFamilies();

// TODO: Add order_by=name query param when backend supports it

function goToPage(pageNum: number) {
  if (pageNum < 1 || pageNum > totalPages.value) return;
  loadPage(pageNum);
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

    <!-- Cards -->
    <div v-else>
      <!-- Empty -->
      <div v-if="families.length === 0" class="flex flex-col items-center justify-center gap-2 py-16">
        <UIcon name="i-lucide-folder-open" class="h-8 w-8 text-muted-foreground/50" />
        <p class="text-sm text-muted-foreground">No model families found</p>
      </div>

      <!-- Card Grid -->
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="(family, index) in families"
          :key="family.id"
          :to="`/settings/model-families/${family.id}`"
          class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
          :style="{ animationDelay: `${index * 30}ms` }"
        >
          <!-- Header: name + provider count -->
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
                {{ family.name }}
              </h3>
              <p class="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                {{ family.family_identifier }}
              </p>
            </div>
            <span class="mt-0.5 shrink-0 text-[10px] text-muted-foreground">
              {{ family.provider_types.length }} provider{{ family.provider_types.length !== 1 ? "s" : "" }}
            </span>
          </div>

          <!-- Description -->
          <p
            v-if="family.description"
            class="mt-2 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground"
          >
            {{ family.description }}
          </p>

          <!-- Spacer -->
          <div class="flex-1" />

          <!-- Provider type badges (pinned to bottom) -->
          <div class="flex flex-wrap gap-1.5 border-t border-border/30 pt-3">
            <span
              v-for="pt in family.provider_types"
              :key="pt"
              class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground"
            >
              {{ pt }}
            </span>
          </div>

          <!-- Edit hint -->
          <div class="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
            <UIcon name="i-lucide-pencil" class="h-3 w-3" />
            Edit
          </div>
        </RouterLink>
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
