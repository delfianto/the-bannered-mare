<script setup lang="ts">
defineProps<{
  active: string;
  categories: string[];
}>();

defineEmits<{
  change: [category: string];
}>();
</script>

<template>
  <div class="scrollbar-hide flex items-center gap-2 overflow-x-auto pb-1">
    <button
      v-for="cat in categories"
      :key="cat"
      class="whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium tracking-wide transition-colors duration-200"
      :class="
        active === cat
          ? 'bg-primary text-primary-foreground'
          : 'border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground'
      "
      @click="$emit('change', cat)"
    >
      {{ cat }}
    </button>
  </div>
</template>
