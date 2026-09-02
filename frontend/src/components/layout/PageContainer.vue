<script setup lang="ts">
interface Props {
  title?: string;
  subtitle?: string;
  spacingClass?: string;
  animate?: boolean;
}

withDefaults(defineProps<Props>(), {
  title: "",
  subtitle: "",
  spacingClass: "space-y-8",
  animate: true,
});
</script>

<template>
  <div class="flex min-h-full w-full flex-1 flex-col p-8 lg:px-12" :class="[spacingClass]">
    <!-- Header (Optional) -->
    <header
      v-if="title || $slots.header || $slots.headerActions"
      class="shrink-0"
      :class="{ 'animate-fade-in-up': animate }"
    >
      <slot name="header">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="mb-1 font-story text-2xl font-bold tracking-wide text-foreground">
              {{ title }}
            </h1>
            <p v-if="subtitle" class="text-sm text-muted-foreground">
              {{ subtitle }}
            </p>
          </div>
          <div v-if="$slots.headerActions" class="flex shrink-0 items-center gap-3">
            <slot name="headerActions" />
          </div>
        </div>
      </slot>
    </header>

    <!-- Main Content Area -->
    <div
      class="flex flex-1 flex-col"
      :class="{ 'animate-fade-in-up': animate }"
      style="animation-delay: 40ms"
    >
      <slot />
    </div>
  </div>
</template>
