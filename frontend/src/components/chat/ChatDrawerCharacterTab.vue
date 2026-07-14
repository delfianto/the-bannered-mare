<script setup lang="ts">
import { watch } from "vue";
import { fallbackAvatarUrl } from "@/utils/avatar";
import { useCharacter } from "@/composables/useCharacter";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";

const props = defineProps<{ characterId: string }>();

const { character: fullCharacter, loading: characterLoading, load: loadCharacter } = useCharacter();

// Lazy-load the full record when this tab mounts / the chat's character changes;
// the composable dedupes by id so re-opening the same character won't refetch.
watch(
  () => props.characterId,
  (id) => {
    if (id) void loadCharacter(id);
  },
  { immediate: true },
);

function portraitSrc(): string {
  const c = fullCharacter.value;
  if (!c) return "";
  // Large tier (<=512px): the drawer portrait renders a few hundred px wide, so
  // the large avatar stays sharp while far lighter than the original.
  return c.avatar_large || c.avatar || fallbackAvatarUrl(c.name, 400);
}

function genderLabel(): string {
  const c = fullCharacter.value;
  if (!c?.gender) return "";
  if (c.gender === "others" && c.custom_gender) return c.custom_gender;
  return c.gender.charAt(0).toUpperCase() + c.gender.slice(1);
}
</script>

<template>
  <div class="p-4">
    <div v-if="characterLoading && !fullCharacter" class="flex justify-center py-12">
      <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="fullCharacter" class="space-y-4">
      <!-- Portrait -->
      <div class="overflow-hidden rounded-xl border bg-base-100/50">
        <img
          :src="portraitSrc()"
          :alt="fullCharacter.name"
          class="aspect-3/4 w-full object-cover object-top"
        />
      </div>

      <div class="text-center">
        <h3 class="font-cinzel text-base font-semibold tracking-wide text-foreground">
          {{ fullCharacter.name }}
        </h3>
      </div>

      <!-- Gender / species / tags chips -->
      <div
        v-if="genderLabel() || fullCharacter.species || fullCharacter.tags?.length"
        class="flex flex-wrap justify-center gap-1.5"
      >
        <span
          v-if="genderLabel()"
          class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
        >
          {{ genderLabel() }}
        </span>
        <span
          v-if="fullCharacter.species"
          class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
        >
          {{ fullCharacter.species }}
        </span>
        <span
          v-for="tag in fullCharacter.tags ?? []"
          :key="tag"
          class="rounded-full bg-base-300 px-2.5 py-0.5 text-[0.625rem] font-medium tracking-wide text-base-content uppercase"
        >
          {{ tag }}
        </span>
      </div>

      <!-- Long-form fields (only when present) -->
      <div class="space-y-2">
        <CollapsibleField
          v-if="fullCharacter.description"
          :label="$t('characters.detail.description')"
          :content="fullCharacter.description"
        />
        <CollapsibleField
          v-if="fullCharacter.personality"
          :label="$t('characters.detail.personality')"
          :content="fullCharacter.personality"
        />
        <CollapsibleField
          v-if="fullCharacter.scenario"
          :label="$t('characters.detail.scenario')"
          :content="fullCharacter.scenario"
        />
      </div>
    </div>

    <div v-else class="py-12 text-center text-xs text-muted-foreground">
      {{ $t("characters.notFound") }}
    </div>
  </div>
</template>
