<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
    <header class="shrink-0 px-12 pt-8 pb-4">
      <div class="animate-fade-in-up">
        <h1 class="mb-1 font-story text-2xl font-bold tracking-wide text-foreground">
          {{ title }}
        </h1>
        <p v-if="subtitle" class="text-sm text-muted-foreground">
          {{ subtitle }}
        </p>
      </div>
    </header>

    <div class="shrink-0 animate-fade-in-up" style="animation-delay: 80ms">
      <slot name="tabs" />
    </div>

    <div class="flex-1 overflow-y-auto px-12 py-6">
      <slot />
    </div>
  </div>
</template>
