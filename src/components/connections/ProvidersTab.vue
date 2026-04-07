<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useProviders } from "@/composables/useProviders";

import anthropicIcon from "@/assets/icons/anthropic.svg";
import googleIcon from "@/assets/icons/google.svg";
import ollamaIcon from "@/assets/icons/ollama.svg";
import openaiIcon from "@/assets/icons/openai.svg";
import openrouterIcon from "@/assets/icons/openrouter.svg";
import xaiIcon from "@/assets/icons/xai.svg";
import otherIcon from "@/assets/icons/other.svg";

const router = useRouter();
const { providers, loading, error, refresh } = useProviders();

const sortedProviders = computed(() =>
  [...providers.value].sort((a, b) => a.name.localeCompare(b.name)),
);

const providerIcons: Record<string, string> = {
  openai: openaiIcon,
  anthropic: anthropicIcon,
  google: googleIcon,
  ollama: ollamaIcon,
  openrouter: openrouterIcon,
  xai: xaiIcon,
  custom: otherIcon,
};

function getIcon(providerType: string): string {
  return providerIcons[providerType] || otherIcon;
}

function formatUrl(url: string | null): string {
  if (!url) return "No URL configured";
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="refresh"
      >
        Retry
      </button>
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="(provider, index) in sortedProviders"
        :key="provider.id"
        class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border border-[var(--border)] bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
        @click="router.push(`/settings/providers/${provider.id}`)"
      >
        <!-- Header: icon + name + status -->
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-accent p-1.5">
              <img :src="getIcon(provider.provider_type)" :alt="provider.provider_type" class="h-full w-full object-contain dark:invert" />
            </div>
            <div class="min-w-0">
              <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
                {{ provider.name }}
              </h3>
              <span class="text-[10px] uppercase tracking-wide text-muted-foreground">
                {{ provider.provider_type }}
              </span>
            </div>
          </div>
          <span
            class="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
            :class="provider.enabled ? 'bg-emerald-500' : 'bg-red-400'"
            :title="provider.enabled ? 'Enabled' : 'Disabled'"
          />
        </div>

        <!-- Spacer -->
        <div class="flex-1" />

        <!-- Details (pinned to bottom area) -->
        <div class="space-y-1.5 border-t border-border/30 pt-3 text-[11px] text-muted-foreground">
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-link" class="h-3 w-3 shrink-0" />
            <span class="truncate">{{ formatUrl(provider.base_url) }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-key" class="h-3 w-3 shrink-0" />
            <span v-if="provider.api_key_configured" class="text-emerald-500">Configured</span>
            <span v-else class="text-amber-500">Not configured</span>
          </div>
        </div>

        <!-- Edit hint -->
        <div class="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
          <UIcon name="i-lucide-pencil" class="h-3 w-3" />
          Edit
        </div>
      </div>
    </div>
  </div>
</template>
