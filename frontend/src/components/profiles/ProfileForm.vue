<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { Profile, ProfileCreate } from "@/composables/useProfiles";
import type { PromptTemplate } from "@/composables/usePromptTemplates";
import type { Preset } from "@/composables/usePresets";
import type { Persona } from "@/composables/usePersonas";
import type { ModelListItem } from "@/composables/useModels";

const props = defineProps<{
  initial?: Profile | null;
  templates: PromptTemplate[];
  presets: Preset[];
  personas: Persona[];
  models: ModelListItem[];
  saving?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: ProfileCreate];
  cancel: [];
}>();

const { t } = useI18n();

// Reka UI's Combobox forbids an item value of "" (it reserves the empty string
// for the cleared state), so the "None" option uses a sentinel that maps back
// to null on submit.
const NONE = "__none__";

const name = ref("");
const description = ref("");
const isDefault = ref(false);
const templateId = ref(NONE);
const presetId = ref(NONE);
const personaId = ref(NONE);
const modelId = ref(NONE);

watch(
  () => props.initial,
  (p) => {
    name.value = p?.name ?? "";
    description.value = p?.description ?? "";
    isDefault.value = p?.is_default ?? false;
    templateId.value = p?.prompt_template_id ?? NONE;
    presetId.value = p?.preset_id ?? NONE;
    personaId.value = p?.persona_id ?? NONE;
    modelId.value = p?.model_id ?? NONE;
  },
  { immediate: true },
);

type Named = { id: string; name: string };

// NONE is the unset/None option; mapped back to null on submit.
function toOptions(list: Named[]) {
  return [
    { label: t("profiles.none"), value: NONE },
    ...list.map((x) => ({ label: x.name, value: x.id })),
  ];
}

function labelFor(list: Named[], id: string) {
  return list.find((x) => x.id === id)?.name ?? t("profiles.none");
}

// Stable option arrays. Recomputing toOptions() inline on every render hands the
// combobox a new array each time, forcing a full keyed re-patch of its list —
// which crashes Reka UI's popper on a large list (the ~75 models).
const templateOptions = computed(() => toOptions(props.templates));
const presetOptions = computed(() => toOptions(props.presets));
const personaOptions = computed(() => toOptions(props.personas));

// A loadout should only offer usable models: enabled, and on an enabled provider.
// A model already selected on an existing loadout is kept even if it has since
// been disabled, so opening that loadout to edit doesn't silently drop its model.
const isModelActive = (m: ModelListItem) => m.enabled && m.provider_enabled;

const modelOptions = computed(() => {
  const usable = props.models.filter(isModelActive);
  if (modelId.value !== NONE && !usable.some((m) => m.id === modelId.value)) {
    const current = props.models.find((m) => m.id === modelId.value);
    if (current) usable.push(current);
  }
  return toOptions(usable);
});

function onSubmit() {
  if (!name.value.trim()) return;
  emit("submit", {
    name: name.value.trim(),
    description: description.value.trim() || null,
    is_default: isDefault.value,
    prompt_template_id: templateId.value === NONE ? null : templateId.value,
    preset_id: presetId.value === NONE ? null : presetId.value,
    persona_id: personaId.value === NONE ? null : personaId.value,
    model_id: modelId.value === NONE ? null : modelId.value,
  });
}

const selectUi = {
  base: "border-none shadow-none ring-0 outline-none p-0 bg-transparent w-full",
  content: "border bg-card ring-0 outline-none shadow-lg",
  item: "text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent",
};
</script>

<template>
  <div class="animate-fade-in-up rounded-xl border bg-card/50 p-6">
    <h2 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
      {{ initial ? $t("profiles.form.editTitle") : $t("profiles.form.newTitle") }}
    </h2>

    <div class="space-y-4">
      <label class="block">
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
          $t("profiles.form.name")
        }}</span>
        <input
          v-model="name"
          type="text"
          :placeholder="$t('profiles.form.namePlaceholder')"
          class="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
        />
      </label>

      <label class="block">
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
          $t("profiles.form.description")
        }}</span>
        <textarea
          v-model="description"
          rows="2"
          :placeholder="$t('profiles.form.descriptionPlaceholder')"
          class="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
        />
      </label>

      <!-- Loadout selectors -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("profiles.fields.template")
          }}</span>
          <USelectMenu
            v-model="templateId"
            :items="templateOptions"
            value-key="value"
            :search-input="false"
            :ui="selectUi"
          >
            <button
              type="button"
              class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-foreground outline-none"
            >
              <span class="flex min-w-0 items-center gap-2">
                <UIcon name="i-lucide-scroll-text" class="size-4 shrink-0 text-muted-foreground" />
                <span class="truncate">{{ labelFor(templates, templateId) }}</span>
              </span>
              <UIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
            </button>
          </USelectMenu>
        </div>

        <div>
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("profiles.fields.preset")
          }}</span>
          <USelectMenu
            v-model="presetId"
            :items="presetOptions"
            value-key="value"
            :search-input="false"
            :ui="selectUi"
          >
            <button
              type="button"
              class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-foreground outline-none"
            >
              <span class="flex min-w-0 items-center gap-2">
                <UIcon
                  name="i-lucide-sliders-horizontal"
                  class="size-4 shrink-0 text-muted-foreground"
                />
                <span class="truncate">{{ labelFor(presets, presetId) }}</span>
              </span>
              <UIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
            </button>
          </USelectMenu>
        </div>

        <div>
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("profiles.fields.persona")
          }}</span>
          <USelectMenu
            v-model="personaId"
            :items="personaOptions"
            value-key="value"
            :search-input="false"
            :ui="selectUi"
          >
            <button
              type="button"
              class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-foreground outline-none"
            >
              <span class="flex min-w-0 items-center gap-2">
                <UIcon name="i-lucide-user" class="size-4 shrink-0 text-muted-foreground" />
                <span class="truncate">{{ labelFor(personas, personaId) }}</span>
              </span>
              <UIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
            </button>
          </USelectMenu>
        </div>

        <div>
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("profiles.fields.model")
          }}</span>
          <USelectMenu
            v-model="modelId"
            :items="modelOptions"
            value-key="value"
            :search-input="true"
            :ui="selectUi"
          >
            <button
              type="button"
              class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-foreground outline-none"
            >
              <span class="flex min-w-0 items-center gap-2">
                <UIcon name="i-lucide-cpu" class="size-4 shrink-0 text-muted-foreground" />
                <span class="truncate">{{ labelFor(models, modelId) }}</span>
              </span>
              <UIcon name="i-lucide-chevron-down" class="size-4 shrink-0 text-muted-foreground" />
            </button>
          </USelectMenu>
        </div>
      </div>

      <!-- Default toggle -->
      <button
        type="button"
        class="flex w-full items-center justify-between rounded-lg border bg-muted/40 px-3 py-2.5"
        role="switch"
        :aria-checked="isDefault"
        @click="isDefault = !isDefault"
      >
        <span class="flex items-center gap-2 text-sm text-foreground">
          <UIcon name="i-lucide-star" class="size-4 text-muted-foreground" />
          {{ $t("profiles.form.setDefault") }}
        </span>
        <span
          class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
          :class="isDefault ? 'bg-primary' : 'bg-muted-foreground/40'"
        >
          <span
            class="size-4 rounded-full shadow-sm transition-transform duration-300"
            :class="isDefault ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
          />
        </span>
      </button>

      <!-- Footer -->
      <div class="flex items-center gap-3 pt-1">
        <button
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          :disabled="saving || !name.trim()"
          @click="onSubmit"
        >
          {{ initial ? $t("profiles.form.save") : $t("profiles.form.create") }}
        </button>
        <button
          class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="$emit('cancel')"
        >
          {{ $t("common.cancel") }}
        </button>
      </div>
    </div>
  </div>
</template>
