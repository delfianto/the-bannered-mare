<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import ConnectionsTabs from "@/components/connections/ConnectionsTabs.vue";
import ProvidersTab from "@/components/connections/ProvidersTab.vue";
import ModelsTab from "@/components/connections/ModelsTab.vue";
import ModelFamiliesTab from "@/components/connections/ModelFamiliesTab.vue";
import PresetsTab from "@/components/connections/PresetsTab.vue";
import TemplatesTab from "@/components/connections/TemplatesTab.vue";
import FragmentsTab from "@/components/connections/FragmentsTab.vue";

const route = useRoute();
const router = useRouter();

const validTabs = ["providers", "models", "model-families", "presets", "templates", "fragments"];

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
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header class="flex-shrink-0 px-12 pt-8 pb-4">
      <div class="animate-fade-in-up">
        <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
          Connections
        </h1>
        <p class="text-sm text-muted-foreground">
          Manage providers, models, presets, templates, and fragments
        </p>
      </div>
    </header>

    <!-- Tabs -->
    <div class="animate-fade-in-up" style="animation-delay: 80ms">
      <ConnectionsTabs :active-tab="activeTab" @change="activeTab = $event" />
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-y-auto px-12 py-6">
      <ProvidersTab v-if="activeTab === 'providers'" />
      <ModelsTab v-if="activeTab === 'models'" />
      <ModelFamiliesTab v-if="activeTab === 'model-families'" />
      <PresetsTab v-if="activeTab === 'presets'" />
      <TemplatesTab v-if="activeTab === 'templates'" />
      <FragmentsTab v-if="activeTab === 'fragments'" />
    </div>
  </div>
</template>
