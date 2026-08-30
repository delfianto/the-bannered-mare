<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <div class="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
    <p class="font-cinzel text-6xl font-bold text-primary">404</p>
    <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
      {{ $t("notFound.title") }}
    </h1>
    <p class="max-w-md text-sm text-muted-foreground">{{ $t("notFound.message") }}</p>
    <RouterLink
      to="/"
      class="mt-2 flex h-10 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-medium text-primary-content transition-all hover:bg-primary/95 active:scale-0.96"
    >
      <AppIcon name="i-lucide-home" />
      {{ $t("notFound.home") }}
    </RouterLink>
  </div>
</template>
