<script setup lang="ts">
import { onMounted } from "vue";
import AppShell from "@/components/layout/AppShell.vue";
import { useSettingsStore } from "@/stores/settings";
import { useTheme } from "@/composables/useTheme";

const settingsStore = useSettingsStore();

useTheme();

onMounted(() => {
  settingsStore.fetchParameterDocs();
});
</script>

<template>
  <UApp>
    <AppShell />
  </UApp>
</template>
