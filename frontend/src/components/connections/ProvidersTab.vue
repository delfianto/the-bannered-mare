<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useProviders } from "@/composables/useProviders";
import { useProvider } from "@/composables/useProvider";
import { useAppToast } from "@/composables/useToast";
import type { components } from "@/api/schema";
import Modal from "@/components/shared/Modal.vue";
import ProviderForm from "./ProviderForm.vue";

const { t } = useI18n();

import anthropicIcon from "@/assets/icons/anthropic.svg";
import googleIcon from "@/assets/icons/google.svg";
import ollamaIcon from "@/assets/icons/ollama.svg";
import openaiIcon from "@/assets/icons/openai.svg";
import openrouterIcon from "@/assets/icons/openrouter.svg";
import xaiIcon from "@/assets/icons/xai.svg";
import otherIcon from "@/assets/icons/other.svg";

const { providers, loading, error, refresh } = useProviders();
const { createProvider, saving } = useProvider();
const toast = useAppToast();

const showCreate = ref(false);

async function onCreate(payload: components["schemas"]["ProviderCreate"]) {
  try {
    await createProvider(payload);
    toast.success(t("connections.provider.toast.created"));
    showCreate.value = false;
    await refresh();
  } catch {
    toast.error(t("connections.provider.toast.createFailed"));
  }
}

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
  if (!url) return t("connections.noUrlConfigured");
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
</script>

<template>
  <div>
    <!-- Primary action lives on the tab bar (see ConnectionsTabs) -->
    <Teleport defer to="#connections-tab-action">
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="showCreate = true"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("connections.newProvider") }}
      </button>
    </Teleport>

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

    <!-- Grid (compact cards) -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <RouterLink
        v-for="(provider, index) in sortedProviders"
        :key="provider.id"
        :to="`/settings/providers/${provider.id}`"
        class="group flex animate-fade-in-up cursor-pointer flex-col gap-2.5 rounded-xl border bg-base-200/50 p-3 transition-all hover:border-muted-foreground/20 hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
      >
        <!-- Header: icon + name + enabled -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex min-w-0 items-center gap-2">
            <div
              class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-base-300 p-1.5"
            >
              <img
                :src="getIcon(provider.provider_type)"
                :alt="provider.provider_type"
                class="size-full object-contain dark:invert"
              />
            </div>
            <div class="min-w-0">
              <h3 class="truncate font-cinzel text-sm font-semibold tracking-wide text-foreground">
                {{ provider.name }}
              </h3>
              <span class="text-3xs tracking-wide text-muted-foreground uppercase">
                {{ provider.provider_type }}
              </span>
            </div>
          </div>
          <span
            class="size-2.5 shrink-0 rounded-full"
            :class="provider.enabled ? 'bg-success' : 'bg-error'"
            :title="provider.enabled ? 'Enabled' : 'Disabled'"
          />
        </div>

        <!-- Info line: url + key status -->
        <div class="flex items-center justify-between gap-2 text-2xs text-muted-foreground">
          <span class="flex min-w-0 items-center gap-1.5">
            <AppIcon name="i-lucide-link" class="size-3 shrink-0" />
            <span class="truncate">{{ formatUrl(provider.base_url) }}</span>
          </span>
          <span class="flex shrink-0 items-center gap-1.5">
            <AppIcon name="i-lucide-key" class="size-3 shrink-0" />
            <!-- Local providers (no env var) never need a key — show neutral, not a warning -->
            <span v-if="!provider.env_var_name">{{ $t("connections.provider.keyNotSet") }}</span>
            <span v-else-if="provider.api_key_configured" class="text-success">{{
              $t("connections.provider.keyConfigured")
            }}</span>
            <span v-else class="text-warning">{{ $t("connections.provider.keyNotSet") }}</span>
          </span>
        </div>
      </RouterLink>
    </div>

    <!-- Create modal -->
    <Modal
      :show="showCreate"
      :title="$t('connections.newProvider')"
      max-width="lg"
      @close="showCreate = false"
    >
      <ProviderForm :saving="saving" @submit="onCreate" @cancel="showCreate = false" />
    </Modal>
  </div>
</template>
