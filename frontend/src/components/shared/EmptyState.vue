<script setup lang="ts">
interface Props {
  icon?: string;
  title?: string;
  description?: string;
  actionLabel?: string;
  hasFilters?: boolean;
}

withDefaults(defineProps<Props>(), {
  icon: "i-lucide-flame",
  title: "",
  description: "",
  actionLabel: "",
  hasFilters: false,
});

defineEmits<{
  action: [];
}>();
</script>

<template>
  <div
    class="flex w-full flex-1 animate-fade-in-up flex-col items-center justify-start px-4 pt-[12vh] pb-12 text-center"
  >
    <!-- Icon with pulsing glow -->
    <div class="relative mb-6">
      <div class="absolute inset-0 animate-pulse rounded-full bg-primary/20 blur-xl" />
      <div class="relative flex size-16 items-center justify-center rounded-full bg-primary/10">
        <AppIcon :name="icon" class="size-8 text-primary" />
      </div>
    </div>

    <h3 class="mb-2 font-cinzel text-lg font-semibold text-foreground">
      <slot name="title">
        {{ title || (hasFilters ? $t("characters.noFound") : $t("characters.libraryAwaits")) }}
      </slot>
    </h3>
    <p class="mb-6 max-w-sm text-sm text-muted-foreground">
      <slot name="description">
        {{
          description || (hasFilters ? $t("characters.tryFilters") : $t("characters.createFirst"))
        }}
      </slot>
    </p>

    <slot name="action">
      <button
        v-if="actionLabel || (!hasFilters && !title)"
        class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
        @click="$emit('action')"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ actionLabel || $t("characters.createNew") }}
      </button>
    </slot>
  </div>
</template>
