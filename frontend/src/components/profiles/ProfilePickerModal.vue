<script setup lang="ts">
import { ref } from "vue";
import Modal from "@/components/shared/Modal.vue";
import { usePromptTemplates } from "@/composables/usePromptTemplates";
import { useModels } from "@/composables/useModels";
import type { components } from "@/api/schema";

type Profile = components["schemas"]["ProfileResponse"];

const props = defineProps<{
  profiles: Profile[];
}>();

const emit = defineEmits<{
  choose: [profileId: string];
  cancel: [];
}>();

const { templates } = usePromptTemplates();
const { models } = useModels({ pageSize: 100 });

// Pre-select the default loadout (falling back to the first) so the user can
// just confirm — while still being free to pick another for this one tale.
const selectedId = ref<string>(
  props.profiles.find((p) => p.is_default)?.id ?? props.profiles[0]?.id ?? "",
);

function resolve(
  list: { id: string; name: string }[],
  id: string | null | undefined,
): string | null {
  if (!id) return null;
  return list.find((x) => x.id === id)?.name ?? null;
}

// Models are registries keyed by display_name rather than the generic `name`.
function resolveModel(id: string | null | undefined): string | null {
  if (!id) return null;
  return models.value.find((m) => m.id === id)?.display_name ?? null;
}
</script>

<template>
  <Modal show title="Choose a Profile" max-width="sm" @close="emit('cancel')">
    <p class="mb-3 text-xs text-muted-foreground">
      Your default loadout is pre-selected — start with it, or pick another for this tale.
    </p>
    <div class="max-h-80 space-y-2 overflow-y-auto">
      <label
        v-for="profile in profiles"
        :key="profile.id"
        class="flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition-colors"
        :class="
          selectedId === profile.id
            ? 'border-primary/50 bg-base-300/30'
            : 'border-border bg-base-300/40 hover:bg-base-300'
        "
      >
        <input
          type="radio"
          name="profile-pick"
          class="radio radio-sm radio-primary mt-0.5 shrink-0"
          :checked="selectedId === profile.id"
          :aria-label="profile.name"
          @change="selectedId = profile.id"
        />
        <span class="min-w-0 flex-1">
          <span class="flex w-full items-center gap-2 text-sm font-medium text-foreground">
            {{ profile.name }}
            <AppIcon v-if="profile.is_default" name="i-lucide-star" class="size-3.5 text-primary" />
          </span>
          <span class="block text-2xs text-muted-foreground">
            {{
              [resolveModel(profile.model_id), resolve(templates, profile.prompt_template_id)]
                .filter(Boolean)
                .join(" • ") || "No model or template set"
            }}
          </span>
        </span>
      </label>
    </div>

    <template #footer>
      <button
        type="button"
        class="h-9 rounded-xl border border-border bg-transparent px-4 text-sm font-medium text-foreground transition-colors hover:bg-base-content/5"
        @click="emit('cancel')"
      >
        Cancel
      </button>
      <button
        type="button"
        :disabled="!selectedId"
        class="h-9 rounded-xl bg-primary px-4 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-40"
        @click="emit('choose', selectedId)"
      >
        Start tale
      </button>
    </template>
  </Modal>
</template>
