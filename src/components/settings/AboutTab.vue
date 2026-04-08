<script setup lang="ts">
import { APP_INFO } from "@/constants/appInfo";
</script>

<template>
  <div class="flex justify-center animate-fade-in-up">
    <div class="w-full max-w-md rounded-xl border bg-card/50 p-8 text-center">
      <!-- App Icon -->
      <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary">
        <UIcon name="i-lucide-flame" class="h-8 w-8 text-primary-foreground" />
      </div>

      <!-- App Name -->
      <h2 class="font-cinzel text-2xl font-bold tracking-wider text-foreground">
        {{ APP_INFO.name }}
      </h2>

      <!-- Tagline -->
      <p class="mt-2 text-sm italic text-muted-foreground">
        {{ APP_INFO.description }}
      </p>

      <!-- Version -->
      <div class="mt-4">
        <UBadge :label="APP_INFO.version" size="md" variant="subtle" color="primary" />
      </div>

      <!-- Divider -->
      <div class="mx-auto my-5 h-px w-24 bg-border" />

      <!-- License -->
      <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <UIcon name="i-lucide-scale" class="h-4 w-4" />
        <span>{{ APP_INFO.license }}</span>
      </div>

      <!-- GitHub Link -->
      <div class="mt-4">
        <UButton
          :to="APP_INFO.github"
          target="_blank"
          icon="i-lucide-github"
          label="View on GitHub"
          variant="outline"
          size="sm"
        />
      </div>

      <!-- Author -->
      <p class="mt-5 text-xs text-muted-foreground">
        Crafted with care by
        <span class="font-medium text-foreground">{{ APP_INFO.author }}</span>
      </p>
    </div>
  </div>
</template>
