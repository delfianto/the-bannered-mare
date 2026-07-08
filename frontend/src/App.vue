<script setup lang="ts">
import { onMounted } from "vue";
import AppShell from "@/components/layout/AppShell.vue";
import ToastContainer from "@/components/shared/ToastContainer.vue";
import { useSettingsStore } from "@/stores/settings";
import { useTheme } from "@/composables/useTheme";

const settingsStore = useSettingsStore();

useTheme();

onMounted(() => {
  settingsStore.fetchParameterDocs();
});
</script>

<template>
  <AppShell />
  <ToastContainer />
</template>
