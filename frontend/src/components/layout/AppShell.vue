<script setup lang="ts">
import AppSidebar from "./AppSidebar.vue";
import ServerStatusBanner from "./ServerStatusBanner.vue";
</script>

<template>
  <div
    class="flex h-screen overflow-hidden bg-base-100 text-foreground transition-colors duration-400"
  >
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-y-auto">
      <ServerStatusBanner />
      <RouterView />
    </main>
  </div>
</template>
