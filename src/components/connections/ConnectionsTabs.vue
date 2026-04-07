<script setup lang="ts">
defineProps<{
  activeTab: string;
}>();

const emit = defineEmits<{
  change: [tab: string];
}>();

const tabs = [
  { id: "providers", label: "Providers", icon: "i-lucide-server" },
  { id: "models", label: "Models", icon: "i-lucide-cpu" },
  { id: "model-families", label: "Model Families", icon: "i-lucide-layers" },
];
</script>

<template>
  <div class="flex-shrink-0 border-b border-border bg-background/60">
    <div class="flex items-center gap-1 px-8">
      <div class="flex items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
          :class="
            activeTab === tab.id
              ? 'text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          "
          @click="emit('change', tab.id)"
        >
          <UIcon :name="tab.icon" class="h-4 w-4" />
          <span class="font-cinzel tracking-wide">{{ tab.label }}</span>
          <span
            v-if="activeTab === tab.id"
            class="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-primary transition-all"
          />
        </button>
      </div>
    </div>
  </div>
</template>
