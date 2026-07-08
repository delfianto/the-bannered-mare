<script setup lang="ts">
import { APP_INFO } from "@/constants/appInfo";
</script>

<template>
  <div class="flex animate-fade-in-up justify-center">
    <div class="w-full max-w-md rounded-xl border bg-base-200/50 p-8 text-center">
      <!-- App Icon -->
      <div class="mx-auto mb-4 flex size-14 items-center justify-center rounded-xl bg-primary">
        <AppIcon name="i-lucide-flame" class="size-8 text-primary-content" />
      </div>

      <!-- App Name -->
      <h2 class="font-cinzel text-2xl font-bold tracking-wider text-foreground">
        {{ APP_INFO.name }}
      </h2>

      <!-- Tagline -->
      <p class="mt-2 text-sm text-muted-foreground italic">
        {{ APP_INFO.description }}
      </p>

      <!-- Version -->
      <div class="mt-4">
        <span
          class="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
        >
          {{ APP_INFO.version }}
        </span>
      </div>

      <!-- Divider -->
      <div class="mx-auto my-5 h-px w-24 bg-border" />

      <!-- License -->
      <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <AppIcon name="i-lucide-scale" class="size-4" />
        <span>{{ APP_INFO.license }}</span>
      </div>

      <!-- GitHub Link -->
      <div class="mt-4">
        <a
          :href="APP_INFO.github"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
        >
          <AppIcon name="i-lucide-github" class="size-4" />
          {{ $t("settings.about.viewGithub") }}
        </a>
      </div>

      <!-- Author -->
      <p class="mt-5 text-xs text-muted-foreground">
        {{ $t("settings.about.craftedBy") }}
        <span class="font-medium text-foreground">{{ APP_INFO.author }}</span>
      </p>
    </div>
  </div>
</template>
