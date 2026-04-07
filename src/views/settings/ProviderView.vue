<script setup lang="ts">
import { reactive, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useProvider } from "@/composables/useProvider";
import { useAppToast } from "@/composables/useToast";

const router = useRouter();
const route = useRoute();
const { provider, loading, saving, error, fetchProvider, saveProvider } = useProvider();
const toast = useAppToast();

const providerTypeIcons: Record<string, string> = {
  openai: "i-lucide-bot",
  anthropic: "i-lucide-brain",
  google: "i-lucide-sparkles",
  ollama: "i-lucide-server",
  openrouter: "i-lucide-route",
  xai: "i-lucide-zap",
  custom: "i-lucide-settings",
};

const form = reactive({
  name: "",
  base_url: "",
  enabled: true,
});

onMounted(async () => {
  const id = route.params.id as string;
  await fetchProvider(id);
});

watch(provider, (p) => {
  if (p) {
    form.name = p.name;
    form.base_url = p.base_url || "";
    form.enabled = p.enabled;
  }
});

function toggleEnabled() {
  form.enabled = !form.enabled;
}

async function handleSave() {
  if (!provider.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== provider.value.name) updates.name = form.name;
  if (form.base_url !== (provider.value.base_url || "")) updates.base_url = form.base_url || null;
  if (form.enabled !== provider.value.enabled) updates.enabled = form.enabled;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await saveProvider(provider.value.id, updates);
    toast.success("Provider updated");
  } catch (e) {
    toast.error("Failed to save provider");
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Loading overlay -->
    <div
      v-if="loading"
      class="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">Loading provider...</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="router.back()"
      >
        Go Back
      </button>
    </div>

    <template v-if="provider && !loading">
      <!-- Header -->
      <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="router.push('/connections')"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-plug" class="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Provider
            </h1>
          </div>
        </div>

        <button
          class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
          :disabled="saving"
          @click="handleSave"
        >
          <UIcon
            :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
            class="h-4 w-4"
            :class="{ 'animate-spin': saving }"
          />
          {{ saving ? "Saving..." : "Save" }}
        </button>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-2xl space-y-6">
          <!-- Main form card -->
          <div class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <!-- Provider type badge -->
            <div class="mb-5 flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                <UIcon
                  :name="providerTypeIcons[provider.provider_type] || 'i-lucide-settings'"
                  class="h-5 w-5 text-foreground"
                />
              </div>
              <div>
                <span class="rounded-full bg-accent px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-foreground">
                  {{ provider.provider_type }}
                </span>
                <p class="mt-0.5 text-[10px] text-muted-foreground">Provider Type (read-only)</p>
              </div>
            </div>

            <div class="space-y-4">
              <!-- Name -->
              <div>
                <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Name
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Provider name"
                  class="h-11 w-full rounded-lg border border-[var(--border)] bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Base URL -->
              <div>
                <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Base URL
                </label>
                <input
                  v-model="form.base_url"
                  type="text"
                  placeholder="https://api.example.com/v1"
                  class="h-11 w-full rounded-lg border border-[var(--border)] bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Enabled toggle -->
              <div class="flex items-center justify-between">
                <label class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Enabled
                </label>
                <button @click="toggleEnabled" class="cursor-pointer">
                  <div
                    class="flex h-[22px] w-10 items-center rounded-full px-[3px]"
                    :class="form.enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
                  >
                    <span
                      class="h-4 w-4 rounded-full shadow-sm transition-transform"
                      :class="form.enabled ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
                    />
                  </div>
                </button>
              </div>
            </div>
          </div>

          <!-- API Key section -->
          <div class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
              API Key
            </h2>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted-foreground">Environment Variable</span>
                <code class="rounded bg-accent px-2 py-0.5 text-xs text-foreground">
                  {{ provider.env_var_name || "N/A" }}
                </code>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-muted-foreground">Status</span>
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  :class="
                    provider.api_key_configured
                      ? 'bg-emerald-500/10 text-emerald-500'
                      : 'bg-amber-500/10 text-amber-500'
                  "
                >
                  <span
                    class="h-1.5 w-1.5 rounded-full"
                    :class="provider.api_key_configured ? 'bg-emerald-500' : 'bg-amber-500'"
                  />
                  {{ provider.api_key_configured ? "Configured" : "Not Configured" }}
                </span>
              </div>
            </div>
          </div>

          <!-- Timestamps -->
          <div class="flex items-center justify-between px-1 text-[11px] text-muted-foreground/60">
            <span>Created {{ formatDate(provider.created_at) }}</span>
            <span>Updated {{ formatDate(provider.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
