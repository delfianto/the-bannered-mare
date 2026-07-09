<script setup lang="ts">
import { usePromptTemplates } from "@/composables/usePromptTemplates";

const { templates, loading, error, refresh } = usePromptTemplates();
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="refresh"
      >
        {{ $t("common.retry") }}
      </button>
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="(template, index) in templates"
        :key="template.id"
        :to="`/settings/templates/${template.id}`"
        class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border bg-base-200/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
      >
        <!-- Header -->
        <div class="mb-2 flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ template.name }}
            </h3>
          </div>
          <span
            v-if="template.is_default"
            class="shrink-0 rounded-full bg-base-300 px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide text-foreground uppercase"
          >
            Default
          </span>
        </div>

        <!-- Description -->
        <p
          v-if="template.description"
          class="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
        >
          {{ template.description }}
        </p>

        <!-- Spacer -->
        <div class="flex-1" />

        <!-- Details -->
        <div
          class="space-y-1.5 border-t border-border/30 pt-3 text-[0.6875rem] text-muted-foreground"
        >
          <div v-if="template.max_history_tokens" class="flex items-center gap-1.5">
            <AppIcon name="i-lucide-hash" class="size-3 shrink-0" />
            <span>{{ template.max_history_tokens.toLocaleString() }} max history tokens</span>
          </div>
          <div class="flex items-center gap-1.5">
            <AppIcon name="i-lucide-clock" class="size-3 shrink-0" />
            <span>{{ new Date(template.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <!-- Edit hint -->
        <div
          class="absolute right-3 bottom-3 flex items-center gap-1 text-[0.625rem] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
        >
          <AppIcon name="i-lucide-pencil" class="size-3" />
          {{ $t("common.edit") }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>
