<script setup lang="ts">
withDefaults(
  defineProps<{
    characterCount: number;
    showActions?: boolean;
  }>(),
  {
    showActions: true,
  },
);

defineEmits<{
  import: [];
  createNew: [];
}>();
</script>

<template>
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="font-story text-2xl font-bold tracking-wide text-foreground">
        {{ $t("characters.library") }}
      </h1>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ $t("characters.inCollection", { count: characterCount }) }}
      </p>
    </div>
    <div v-if="showActions" class="flex items-center gap-2">
      <button
        class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-base-300/60"
        @click="$emit('import')"
      >
        <AppIcon name="i-lucide-download" class="size-4" />
        {{ $t("characters.importBtn") }}
      </button>
      <button
        class="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
        @click="$emit('createNew')"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("characters.createNew") }}
      </button>
    </div>
  </div>
</template>
