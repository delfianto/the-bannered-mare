<script setup lang="ts">
defineProps<{
  hasFilters: boolean;
}>();

defineEmits<{
  createNew: [];
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center px-4 py-20 text-center">
    <!-- Flame icon with pulsing glow -->
    <div class="relative mb-6">
      <div class="absolute inset-0 animate-pulse rounded-full bg-primary/20 blur-xl" />
      <div
        class="relative flex h-16 w-16 items-center justify-center rounded-full bg-primary/10"
      >
        <UIcon name="i-lucide-flame" class="h-8 w-8 text-primary" />
      </div>
    </div>

    <h3 class="mb-2 font-cinzel text-lg font-semibold text-foreground">
      {{ hasFilters ? $t('characters.noFound') : $t('characters.libraryAwaits') }}
    </h3>
    <p class="mb-6 max-w-sm text-sm text-muted-foreground">
      {{
        hasFilters
          ? $t('characters.tryFilters')
          : $t('characters.createFirst')
      }}
    </p>
    <button
      v-if="!hasFilters"
      class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      @click="$emit('createNew')"
    >
      <UIcon name="i-lucide-plus" class="h-4 w-4" />
      {{ $t('characters.createNew') }}
    </button>
  </div>
</template>
