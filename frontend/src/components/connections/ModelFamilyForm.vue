<script setup lang="ts">
import { reactive, computed } from "vue";
import type { components } from "@/api/schema";

type ProviderType = components["schemas"]["ProviderType"];

defineProps<{ saving?: boolean }>();

const emit = defineEmits<{
  submit: [payload: components["schemas"]["ModelFamilyCreate"]];
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
  { value: "custom", label: "Custom" },
];

const form = reactive({
  name: "",
  family_identifier: "",
  description: "",
  provider_types: [] as ProviderType[],
});

const canCreate = computed(() => !!form.name.trim() && !!form.family_identifier.trim());

function toggleProviderType(t: ProviderType) {
  const i = form.provider_types.indexOf(t);
  if (i === -1) form.provider_types.push(t);
  else form.provider_types.splice(i, 1);
}

function onSubmit() {
  if (!canCreate.value) return;
  emit("submit", {
    name: form.name.trim(),
    family_identifier: form.family_identifier.trim(),
    description: form.description.trim() || null,
    provider_types: form.provider_types,
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
        placeholder="e.g. GPT-4 class"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Family identifier -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">Family Identifier</span>
      <input
        v-model="form.family_identifier"
        type="text"
        placeholder="e.g. gpt-4"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Description -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">
        Description <span class="text-muted-foreground/60">(optional)</span>
      </span>
      <textarea
        v-model="form.description"
        rows="2"
        placeholder="What models belong to this family?"
        class="w-full resize-y rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Provider types -->
    <div>
      <span class="mb-1 block text-xs font-medium text-muted-foreground">
        Provider Types <span class="text-muted-foreground/60">(which providers serve it)</span>
      </span>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="pt in providerTypes"
          :key="pt.value"
          type="button"
          class="rounded-full border px-3 py-1 text-xs font-medium transition-colors"
          :class="
            form.provider_types.includes(pt.value)
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-base-300 hover:text-foreground'
          "
          @click="toggleProviderType(pt.value)"
        >
          {{ pt.label }}
        </button>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-3 pt-1">
      <button
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="onSubmit"
      >
        {{ saving ? "Creating…" : "Create Family" }}
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
