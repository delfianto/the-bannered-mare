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
  { id: "profiles", label: t("profiles.tabs.profiles") || "Profiles", icon: "i-lucide-layers" },
  { id: "personas", label: t("profiles.tabs.personas"), icon: "i-lucide-user-circle" },
  { id: "presets", label: t("connections.tabs.presets"), icon: "i-lucide-sliders-horizontal" },
  { id: "templates", label: t("connections.tabs.templates"), icon: "i-lucide-file-text" },
  { id: "fragments", label: t("connections.tabs.fragments"), icon: "i-lucide-puzzle" },
];
</script>

<template>
  <div class="shrink-0 border-b bg-base-100/60">
    <div class="flex items-center gap-1 px-8">
      <div class="flex items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
          :class="
            activeTab === tab.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
          "
          @click="emit('change', tab.id)"
        >
          <AppIcon :name="tab.icon" class="size-4" />
          <span class="font-cinzel tracking-wide">{{ tab.label }}</span>
          <span
            v-if="activeTab === tab.id"
            class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-primary transition-all"
          />
        </button>
      </div>
    </div>
  </div>
</template>
