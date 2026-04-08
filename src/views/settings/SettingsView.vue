<script setup lang="ts">
import { ref } from "vue";
import SettingsTabs from "@/components/settings/SettingsTabs.vue";
import InterfaceTab from "@/components/settings/InterfaceTab.vue";
import PersonaTab from "@/components/settings/PersonaTab.vue";
import LogsTab from "@/components/settings/LogsTab.vue";
import AboutTab from "@/components/settings/AboutTab.vue";

const activeTab = ref("interface");
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header class="flex-shrink-0 px-12 pt-8 pb-4">
      <div class="animate-fade-in-up">
        <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
          Settings
        </h1>
        <p class="text-sm text-muted-foreground">
          Customize your experience and manage your profile
        </p>
      </div>
    </header>

    <!-- Tabs -->
    <div class="animate-fade-in-up" style="animation-delay: 80ms">
      <SettingsTabs :active-tab="activeTab" @change="activeTab = $event" />
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-y-auto px-12 py-6">
      <InterfaceTab v-if="activeTab === 'interface'" />
      <PersonaTab v-if="activeTab === 'persona'" />
      <LogsTab v-if="activeTab === 'logs'" />
      <AboutTab v-if="activeTab === 'about'" />
    </div>
  </div>
</template>
