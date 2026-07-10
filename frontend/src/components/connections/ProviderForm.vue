<script setup lang="ts">
import { reactive, computed } from "vue";
import type { components } from "@/api/schema";

type ProviderType = components["schemas"]["ProviderType"];

defineProps<{ saving?: boolean }>();

const emit = defineEmits<{
  submit: [payload: components["schemas"]["ProviderCreate"]];
  cancel: [];
}>();

const providerTypes: { value: ProviderType; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "xai", label: "xAI" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama" },
  { value: "lmstudio", label: "LM Studio" },
  { value: "opencode", label: "OpenCode Zen" },
  { value: "opencode_go", label: "OpenCode Go" },
  { value: "custom", label: "Custom" },
];

const form = reactive({
  name: "",
  provider_type: "" as ProviderType | "",
  base_url: "",
  api_key_env_var: "",
});

const isCustom = computed(() => form.provider_type === "custom");
const typeName = computed(
  () => providerTypes.find((t) => t.value === form.provider_type)?.label || "Select a type",
);

// Custom providers must declare both a base URL and an API-key env var; other
// provider types must NOT set an env var (the backend rejects it).
const canCreate = computed(
  () =>
    !!form.name.trim() &&
    !!form.provider_type &&
    (!isCustom.value || (!!form.base_url.trim() && !!form.api_key_env_var.trim())),
);

function onSubmit() {
  if (!canCreate.value || !form.provider_type) return;
  emit("submit", {
    name: form.name.trim(),
    provider_type: form.provider_type,
    base_url: form.base_url.trim() || null,
    api_key_env_var: isCustom.value ? form.api_key_env_var.trim() : null,
  });
}
</script>

<template>
  <div class="space-y-4">
    <!-- Name -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">Name</span>
      <input
        v-model="form.name"
        type="text"
        placeholder="Provider name"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Provider type -->
    <div>
      <span class="mb-1 block text-xs font-medium text-muted-foreground">Provider Type</span>
      <SelectMenu
        v-model="form.provider_type"
        :items="providerTypes"
        value-key="value"
        :search-input="false"
      >
        <button
          type="button"
          class="flex h-10 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-100 px-3 text-sm text-foreground outline-none"
        >
          <span class="truncate">{{ typeName }}</span>
          <AppIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
        </button>
      </SelectMenu>
    </div>

    <!-- Base URL -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">
        Base URL
        <span v-if="isCustom" class="text-error">*</span>
        <span v-else class="text-muted-foreground/60">(optional)</span>
      </span>
      <input
        v-model="form.base_url"
        type="text"
        placeholder="https://api.example.com/v1"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
      <span class="mt-1 block text-[0.625rem] text-muted-foreground/70">
        Known providers use a sensible default when left blank.
      </span>
    </label>

    <!-- API key env var (custom only) -->
    <label v-if="isCustom" class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">
        API Key Env Var <span class="text-error">*</span>
      </span>
      <input
        v-model="form.api_key_env_var"
        type="text"
        placeholder="E.G. MY_PROVIDER_API_KEY"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
      <span class="mt-1 block text-[0.625rem] text-muted-foreground/70">
        The environment variable the server reads the API key from.
      </span>
    </label>

    <!-- Footer -->
    <div class="flex items-center gap-3 pt-1">
      <button
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="onSubmit"
      >
        {{ saving ? "Creating…" : "Create Provider" }}
      </button>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
        @click="$emit('cancel')"
      >
        {{ $t("common.cancel") }}
      </button>
    </div>
  </div>
</template>
