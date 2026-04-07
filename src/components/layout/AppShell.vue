<script setup lang="ts">
import AppSidebar from "./AppSidebar.vue";
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-background text-foreground transition-colors duration-400">
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-y-auto">
      <RouterView />
    </main>
  </div>
</template>
