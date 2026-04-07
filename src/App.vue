<script setup lang="ts">
import { onMounted } from "vue";
import AppShell from "@/components/layout/AppShell.vue";
import { useSettingsStore } from "@/stores/settings";
import { useTheme } from "@/composables/useTheme";

const settingsStore = useSettingsStore();

// Initialize theme on app mount
useTheme();

onMounted(() => {
  settingsStore.fetchParameterDocs();
});
</script>

<template>
  <AppShell />
  <UNotifications />
</template>
