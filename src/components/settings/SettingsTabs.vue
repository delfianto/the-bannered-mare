<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

defineProps<{
  activeTab: string;
}>();

const emit = defineEmits<{
  change: [tab: string];
}>();

const tabs = computed(() => [
  { id: "interface", label: t('settings.tabs.interface'), icon: "i-lucide-palette" },
  { id: "persona", label: t('settings.tabs.persona'), icon: "i-lucide-user-circle" },
  { id: "logs", label: t('settings.tabs.logs'), icon: "i-lucide-scroll-text" },
  { id: "about", label: t('settings.tabs.about'), icon: "i-lucide-info" },
]);
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
