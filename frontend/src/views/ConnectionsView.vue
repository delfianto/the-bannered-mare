<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import ConnectionsTabs from "@/components/connections/ConnectionsTabs.vue";
import ProvidersTab from "@/components/connections/ProvidersTab.vue";
import ModelsTab from "@/components/connections/ModelsTab.vue";
import ModelFamiliesTab from "@/components/connections/ModelFamiliesTab.vue";
import TabbedPageContainer from "@/components/layout/TabbedPageContainer.vue";

const route = useRoute();
const router = useRouter();

const validTabs = ["providers", "models", "model-families"];

const activeTab = computed({
  get: () => {
    const tab = route.query.tab as string;
    return validTabs.includes(tab) ? tab : "providers";
  },
  set: (tab: string) => {
    router.replace({ query: { tab } });
  },
});
</script>

<template>
  <TabbedPageContainer :title="$t('connections.title')" :subtitle="$t('connections.subtitle')">
    <template #tabs>
      <ConnectionsTabs :active-tab="activeTab" @change="activeTab = $event" />
    </template>

    <ProvidersTab v-if="activeTab === 'providers'" />
    <ModelsTab v-if="activeTab === 'models'" />
    <ModelFamiliesTab v-if="activeTab === 'model-families'" />
  </TabbedPageContainer>
</template>
