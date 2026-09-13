<script setup lang="ts">
import { ref } from "vue";
import SettingsTabs from "@/components/settings/SettingsTabs.vue";
import InterfaceTab from "@/components/settings/InterfaceTab.vue";
import LogsTab from "@/components/settings/LogsTab.vue";
import AboutTab from "@/components/settings/AboutTab.vue";
import TabbedPageContainer from "@/components/layout/TabbedPageContainer.vue";

const activeTab = ref("interface");
</script>

<template>
  <TabbedPageContainer :title="$t('settings.title')" :subtitle="$t('settings.subtitle')">
    <template #tabs>
      <SettingsTabs :active-tab="activeTab" @change="activeTab = $event" />
    </template>

    <InterfaceTab v-if="activeTab === 'interface'" />
    <LogsTab v-if="activeTab === 'logs'" />
    <AboutTab v-if="activeTab === 'about'" />
  </TabbedPageContainer>
</template>
