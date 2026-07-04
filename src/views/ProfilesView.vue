<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import ProfilesTabs from "@/components/profiles/ProfilesTabs.vue";
import ProfilesTab from "@/components/profiles/ProfilesTab.vue";
import PresetsTab from "@/components/connections/PresetsTab.vue";
import TemplatesTab from "@/components/connections/TemplatesTab.vue";
import FragmentsTab from "@/components/connections/FragmentsTab.vue";

const route = useRoute();
const router = useRouter();

const validTabs = ["profiles", "presets", "templates", "fragments"];

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
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header class="flex-shrink-0 px-12 pt-8 pb-4">
      <div class="animate-fade-in-up">
        <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ $t("profiles.title") }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ $t("profiles.subtitle") }}
        </p>
      </div>
    </header>

    <!-- Tabs -->
    <div class="animate-fade-in-up" style="animation-delay: 80ms">
      <ProfilesTabs :active-tab="activeTab" @change="activeTab = $event" />
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-y-auto px-12 py-6">
      <ProfilesTab v-if="activeTab === 'profiles'" />
      <PresetsTab v-else-if="activeTab === 'presets'" />
      <TemplatesTab v-else-if="activeTab === 'templates'" />
      <FragmentsTab v-else-if="activeTab === 'fragments'" />
    </div>
  </div>
</template>
