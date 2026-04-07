<script setup lang="ts">
defineProps<{
  characterCount: number;
}>();

defineEmits<{
  import: [];
  createNew: [];
}>();
</script>

<template>
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
        Character Library
      </h1>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ characterCount }} character{{ characterCount !== 1 ? "s" : "" }} in your
        collection
      </p>
    </div>
    <div class="flex items-center gap-2">
      <button
        class="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted/60"
        @click="$emit('import')"
      >
        <UIcon name="i-lucide-download" class="h-4 w-4" />
        Import
      </button>
      <button
        class="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        @click="$emit('createNew')"
      >
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        Create New
      </button>
    </div>
  </div>
</template>
