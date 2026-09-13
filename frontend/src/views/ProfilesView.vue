<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import ProfilesTabs from "@/components/profiles/ProfilesTabs.vue";
import ProfilesTab from "@/components/profiles/ProfilesTab.vue";
import PersonaTab from "@/components/profiles/PersonaTab.vue";
import PresetsTab from "@/components/connections/PresetsTab.vue";
import TemplatesTab from "@/components/connections/TemplatesTab.vue";
import FragmentsTab from "@/components/connections/FragmentsTab.vue";
import TabbedPageContainer from "@/components/layout/TabbedPageContainer.vue";

const route = useRoute();
const router = useRouter();

const validTabs = ["profiles", "personas", "presets", "templates", "fragments"];

const activeTab = computed({
  get: () => {
    const tab = route.query.tab as string;
    return validTabs.includes(tab) ? tab : "profiles";
  },
  set: (tab: string) => {
    router.replace({ query: { tab } });
  },
});
</script>

<template>
  <TabbedPageContainer :title="$t('profiles.title')" :subtitle="$t('profiles.subtitle')">
    <template #tabs>
      <ProfilesTabs :active-tab="activeTab" @change="activeTab = $event" />
    </template>

    <ProfilesTab v-if="activeTab === 'profiles'" />
    <PersonaTab v-else-if="activeTab === 'personas'" />
    <PresetsTab v-else-if="activeTab === 'presets'" />
    <TemplatesTab v-else-if="activeTab === 'templates'" />
    <FragmentsTab v-else-if="activeTab === 'fragments'" />
  </TabbedPageContainer>
</template>
