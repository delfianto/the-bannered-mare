<script setup lang="ts">
import Modal from "@/components/shared/Modal.vue";
import { usePromptTemplates } from "@/composables/usePromptTemplates";
import { useModels } from "@/composables/useModels";
import type { components } from "@/api/schema";

type Profile = components["schemas"]["ProfileResponse"];

defineProps<{
  profiles: Profile[];
}>();

const emit = defineEmits<{
  choose: [profileId: string];
  cancel: [];
}>();

const { templates } = usePromptTemplates();
const { models } = useModels({ pageSize: 100 });

function resolve(
  list: { id: string; name: string }[],
  id: string | null | undefined,
): string | null {
  if (!id) return null;
  return list.find((x) => x.id === id)?.name ?? null;
}
</script>

<template>
  <Modal show title="Choose a Profile" max-width="sm" @close="emit('cancel')">
    <p class="mb-3 text-xs text-muted-foreground">
      You have multiple profiles set up. Pick one to use for this tale.
    </p>
    <div class="max-h-80 space-y-2 overflow-y-auto">
      <button
        v-for="profile in profiles"
        :key="profile.id"
        type="button"
        class="flex w-full flex-col items-start gap-0.5 rounded-lg border bg-base-300/40 px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-base-300"
        @click="emit('choose', profile.id)"
      >
        <span class="flex w-full items-center gap-2 text-sm font-medium text-foreground">
          {{ profile.name }}
          <AppIcon v-if="profile.is_default" name="i-lucide-star" class="size-3.5 text-primary" />
        </span>
        <span class="text-[11px] text-muted-foreground">
          {{
            [resolve(models, profile.model_id), resolve(templates, profile.prompt_template_id)]
              .filter(Boolean)
              .join(" • ") || "No model or template set"
          }}
        </span>
      </button>
    </div>

    <template #footer>
      <button
        type="button"
        class="h-9 rounded-xl border border-border bg-transparent px-4 text-sm font-medium text-foreground transition-colors hover:bg-white/5"
        @click="emit('cancel')"
      >
        Cancel
      </button>
    </template>
  </Modal>
</template>
