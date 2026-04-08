<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { t } = useI18n();

defineProps<{
  activeTab: string;
}>();

const emit = defineEmits<{
  change: [tab: string];
}>();

const tabs = [
  { id: "providers", label: t("connections.tabs.providers"), icon: "i-lucide-server" },
  { id: "models", label: t("connections.tabs.models"), icon: "i-lucide-cpu" },
  { id: "model-families", label: t("connections.tabs.modelFamilies"), icon: "i-lucide-layers" },
  { id: "presets", label: t("connections.tabs.presets"), icon: "i-lucide-sliders-horizontal" },
  { id: "templates", label: t("connections.tabs.templates"), icon: "i-lucide-file-text" },
  { id: "fragments", label: t("connections.tabs.fragments"), icon: "i-lucide-puzzle" },
];
</script>

<template>
  <div class="flex-shrink-0 border-b bg-background/60">
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
