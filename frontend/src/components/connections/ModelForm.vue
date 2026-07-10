<script setup lang="ts">
import { reactive, computed, watch } from "vue";
import { providersForFamily } from "@/utils/modelProviderFilter";

const props = defineProps<{
  providers: { id: string; name: string }[];
  families: { id: string; name: string }[];
  prefill?: { provider_id?: string; model_identifier?: string; name?: string };
  saving?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: Record<string, unknown>];
  cancel: [];
}>();

const form = reactive({
  name: props.prefill?.name || "",
  model_identifier: props.prefill?.model_identifier || "",
  provider_id: props.prefill?.provider_id || "",
  model_family_id: "",
  routing_provider_id: "",
  routing_identifier: "",
  enabled: true,
});

const selectedFamily = computed(() =>
  props.families.find((f: any) => f.id === form.model_family_id),
);
const providerItems = computed(() =>
  providersForFamily(props.providers as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...props.families]
    .sort((a: any, b: any) => a.name.localeCompare(b.name))
    .map((f: any) => ({ label: f.name, value: f.id })),
);
const providerName = computed(
  () => props.providers.find((p: any) => p.id === form.provider_id)?.name || "Select a provider",
);
const familyName = computed(
  () => familyItems.value.find((i) => i.value === form.model_family_id)?.label || "Select a family",
);
// "Route via" options: the model's native provider, or any other provider the
// family supports (aggregators like OpenRouter / OpenCode Go / Zen).
const routeItems = computed(() => [
  { label: "Native — use the model's own provider", value: "" },
  ...providersForFamily(props.providers as any, selectedFamily.value as any)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: `Route via ${p.name}`, value: p.id })),
]);
const routeName = computed(
  () => routeItems.value.find((i) => i.value === form.routing_provider_id)?.label || "Native",
);
const isRouted = computed(() => !!form.routing_provider_id);

watch(
  () => form.routing_provider_id,
  (v) => {
    if (!v) form.routing_identifier = "";
  },
);

// Provider is constrained by the family. On family change, drop an incompatible
// provider; restore a prefilled provider (from "Add as Model") once a compatible
// family is chosen.
const prefilledProviderId = props.prefill?.provider_id || "";
watch(
  () => form.model_family_id,
  () => {
    const valid = providerItems.value.some((i) => i.value === form.provider_id);
    if (form.provider_id && !valid) form.provider_id = "";
    if (
      !form.provider_id &&
      prefilledProviderId &&
      providerItems.value.some((i) => i.value === prefilledProviderId)
    ) {
      form.provider_id = prefilledProviderId;
    }
  },
);

const canCreate = computed(
  () =>
    !!form.name.trim() &&
    !!form.model_identifier.trim() &&
    !!form.provider_id &&
    !!form.model_family_id &&
    (!isRouted.value || !!form.routing_identifier.trim()),
);

function toggleEnabled() {
  form.enabled = !form.enabled;
}

function onSubmit() {
  if (!canCreate.value) return;
  emit("submit", {
    name: form.name.trim(),
    model_identifier: form.model_identifier.trim(),
    provider_id: form.provider_id,
    model_family_id: form.model_family_id,
    routing_provider_id: form.routing_provider_id || null,
    routing_identifier: isRouted.value ? form.routing_identifier.trim() || null : null,
    enabled: form.enabled,
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
        placeholder="Model display name"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Model identifier -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">Model Identifier</span>
      <input
        v-model="form.model_identifier"
        type="text"
        placeholder="e.g. openai/gpt-4o"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <!-- Model family -->
      <div>
        <span class="mb-1 block text-xs font-medium text-muted-foreground">Model Family</span>
        <SelectMenu v-model="form.model_family_id" :items="familyItems" value-key="value">
          <button
            type="button"
            class="flex h-10 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-100 px-3 text-sm text-foreground outline-none"
          >
            <span class="truncate">{{ familyName }}</span>
            <AppIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
          </button>
        </SelectMenu>
      </div>

      <!-- Provider (constrained by family) -->
      <div>
        <span class="mb-1 block text-xs font-medium text-muted-foreground">Provider</span>
        <SelectMenu
          v-model="form.provider_id"
          :items="providerItems"
          value-key="value"
          :disabled="!form.model_family_id"
        >
          <button
            type="button"
            :disabled="!form.model_family_id"
            class="flex h-10 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-100 px-3 text-sm text-foreground outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span class="truncate">{{
              form.model_family_id ? providerName : "Select a family first"
            }}</span>
            <AppIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
          </button>
        </SelectMenu>
      </div>
    </div>

    <!-- Routing override -->
    <div class="rounded-lg border bg-base-100 p-3">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">Route via</span>
      <SelectMenu
        v-model="form.routing_provider_id"
        :items="routeItems"
        value-key="value"
        :disabled="!form.model_family_id"
      >
        <button
          type="button"
          :disabled="!form.model_family_id"
          class="flex h-10 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-100 px-3 text-sm text-foreground outline-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span class="truncate">{{
            form.model_family_id ? routeName : "Select a family first"
          }}</span>
          <AppIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
        </button>
      </SelectMenu>
      <input
        v-if="isRouted"
        v-model="form.routing_identifier"
        type="text"
        placeholder="Model id on the routing provider, e.g. deepseek-v4-flash"
        class="mt-3 w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
      <span v-else class="mt-1 block text-[0.625rem] text-muted-foreground">
        Uses the model's own provider ({{ providerName }}).
      </span>
    </div>

    <!-- Enabled -->
    <div class="flex items-center justify-between rounded-lg border bg-base-100 px-3 py-2.5">
      <span class="text-sm text-muted-foreground">Enabled</span>
      <AppToggle :model-value="form.enabled" aria-label="Enabled" @change="toggleEnabled" />
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-3 pt-1">
      <button
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="onSubmit"
      >
        {{ saving ? "Creating…" : "Create Model" }}
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
