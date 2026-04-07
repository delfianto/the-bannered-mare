<script setup lang="ts">
import { useRouter } from "vue-router";
import { useProviders } from "@/composables/useProviders";

const router = useRouter();
const { providers, loading, error, refresh } = useProviders();

const providerTypeIcons: Record<string, string> = {
  openai: "i-lucide-bot",
  anthropic: "i-lucide-brain",
  google: "i-lucide-sparkles",
  ollama: "i-lucide-server",
  openrouter: "i-lucide-route",
  xai: "i-lucide-zap",
  custom: "i-lucide-settings",
};

function getProviderIcon(providerType: string): string {
  return providerTypeIcons[providerType] || "i-lucide-settings";
}

function formatUrl(url: string | null): string {
  if (!url) return "No URL configured";
  try {
    const parsed = new URL(url);
    return parsed.host;
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
    <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div
        v-for="(provider, index) in providers"
        :key="provider.id"
        class="animate-fade-in-up rounded-xl border border-[var(--border)] bg-card/50 p-5 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 60}ms` }"
      >
        <!-- Header -->
        <div class="mb-3 flex items-start justify-between">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
              <UIcon :name="getProviderIcon(provider.provider_type)" class="h-5 w-5 text-foreground" />
            </div>
            <div>
              <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
                {{ provider.name }}
              </h3>
              <span class="rounded-full bg-accent px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-foreground">
                {{ provider.provider_type }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              @click="router.push(`/settings/providers/${provider.id}`)"
            >
              <UIcon name="i-lucide-pencil" class="h-3.5 w-3.5" />
            </button>
            <div class="flex items-center gap-1.5">
              <span
                class="h-2.5 w-2.5 rounded-full"
                :class="provider.enabled ? 'bg-emerald-500' : 'bg-red-500'"
              />
              <span class="text-xs text-muted-foreground">
                {{ provider.enabled ? "Enabled" : "Disabled" }}
              </span>
            </div>
          </div>
        </div>

        <!-- Details -->
        <div class="space-y-2 text-xs text-muted-foreground">
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-link" class="h-3.5 w-3.5 shrink-0" />
            <span class="truncate">{{ formatUrl(provider.base_url) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-key" class="h-3.5 w-3.5 shrink-0" />
            <span v-if="provider.api_key_configured" class="text-emerald-500">
              API key configured
            </span>
            <span v-else class="text-amber-500">
              {{ provider.env_var_name ? `Missing: ${provider.env_var_name}` : "No API key needed" }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
