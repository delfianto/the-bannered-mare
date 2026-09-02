<script setup lang="ts">
interface Tab {
  key: string;
  label: string;
}

defineProps<{
  tabs: Tab[];
  modelValue: string;
}>();

defineEmits<{
  "update:modelValue": [key: string];
}>();
</script>

<template>
  <div class="flex items-center gap-1 border-b px-2">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="relative px-3 py-2.5 text-xs font-medium transition-colors"
      :class="
        modelValue === tab.key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      "
      @click="$emit('update:modelValue', tab.key)"
    >
      <span class="font-story tracking-wide">{{ tab.label }}</span>
      <span
        v-if="modelValue === tab.key"
        class="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-primary transition-all"
      />
    </button>
  </div>
</template>
