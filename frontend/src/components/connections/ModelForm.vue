<script setup lang="ts">
import { reactive, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { providersForFamily } from "@/utils/modelProviderFilter";
import type { components } from "@/api/schema";

type ModelCreate = components["schemas"]["ModelCreate"];
type ProviderResponse = components["schemas"]["ProviderResponse"];
type ModelFamilyListResponse = components["schemas"]["ModelFamilyListResponse"];

const { t } = useI18n();

const props = defineProps<{
  providers: ProviderResponse[];
  families: ModelFamilyListResponse[];
  prefill?: { provider_id?: string; model_identifier?: string; name?: string };
  saving?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: ModelCreate];
  cancel: [];
}>();

const form = reactive({
  name: props.prefill?.name || "",
  model_identifier: props.prefill?.model_identifier || "",
  provider_id: props.prefill?.provider_id || "",
  model_family_id: "",
  enabled: true,
});

const selectedFamily = computed(() =>
  props.families.find((f) => f.id === form.model_family_id),
);
const providerItems = computed(() =>
  providersForFamily(props.providers, selectedFamily.value)
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((p) => ({ label: p.name, value: p.id })),
);
const familyItems = computed(() =>
  [...props.families]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((f) => ({ label: f.name, value: f.id })),
);
const providerName = computed(
  () =>
    props.providers.find((p) => p.id === form.provider_id)?.name ||
    t("connections.model.selectProvider"),
);
// The identifier scheme depends on the chosen provider (the route): OpenRouter
// wants a vendor/model slug, native/OpenCode take the bare name, etc.
const identifierHint = computed(
  () => props.providers.find((p) => p.id === form.provider_id)?.identifier_hint || "",
);
const familyName = computed(
  () =>
    familyItems.value.find((i) => i.value === form.model_family_id)?.label ||
    t("connections.model.selectFamily"),
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
    !!form.model_family_id,
);

function toggleEnabled() {
  form.enabled = !form.enabled;
}

// Create a registry with a single initial route; slug/original_identifier are
// derived server-side from that first route.
function onSubmit() {
  if (!canCreate.value) return;
  emit("submit", {
    display_name: form.name.trim(),
    model_family_id: form.model_family_id,
    enabled: form.enabled,
    routes: [
      {
        provider_id: form.provider_id,
        model_identifier: form.model_identifier.trim(),
        enabled: true,
      },
    ],
  });
}
</script>

<template>
  <div class="space-y-4">
    <!-- Name -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
        $t("connections.model.name")
      }}</span>
      <input
        v-model="form.name"
        type="text"
        :placeholder="$t('connections.model.namePlaceholder')"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
    </label>

    <!-- Model identifier -->
    <label class="block">
      <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
        $t("connections.model.identifier")
      }}</span>
      <input
        v-model="form.model_identifier"
        type="text"
        :placeholder="$t('connections.model.identifierPlaceholder')"
        class="w-full rounded-lg border bg-base-100 px-3 py-2 font-mono text-sm text-foreground placeholder:font-sans placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
      />
      <p v-if="identifierHint" class="mt-1 text-xs text-muted-foreground/70">
        {{ identifierHint }}
      </p>
    </label>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <!-- Model family -->
      <div>
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
          $t("connections.model.family")
        }}</span>
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
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
          $t("connections.model.provider")
        }}</span>
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
              form.model_family_id ? providerName : $t("connections.model.selectFamilyFirst")
            }}</span>
            <AppIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
          </button>
        </SelectMenu>
      </div>
    </div>

    <!-- Enabled -->
    <div class="flex items-center justify-between rounded-lg border bg-base-100 px-3 py-2.5">
      <span class="text-sm text-muted-foreground">{{ $t("connections.model.enabled") }}</span>
      <AppToggle :model-value="form.enabled" aria-label="Enabled" @change="toggleEnabled" />
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-3 pt-1">
      <button
        class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="onSubmit"
      >
        {{ saving ? $t("connections.model.creating") : $t("connections.model.createModel") }}
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
