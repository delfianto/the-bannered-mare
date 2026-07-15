<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { CharacterData } from "@/types/creator";
import { SPECIES_OPTIONS, GENDER_OPTIONS, SUGGESTED_TAGS } from "@/constants/creatorData";
import FormField from "./FormField.vue";
import Combobox from "./Combobox.vue";
import TagInput from "./TagInput.vue";
import AvatarUpload from "./AvatarUpload.vue";
import AutoTextarea from "./AutoTextarea.vue";

const { t } = useI18n();

defineProps<{
  data: CharacterData;
}>();

const emit = defineEmits<{
  "update:field": [field: keyof CharacterData, value: CharacterData[keyof CharacterData]];
  "add:tag": [tag: string];
  "remove:tag": [tag: string];
  change: [file: File];
}>();
</script>

<template>
  <div class="animate-fade-in-up space-y-6">
    <div>
      <h2
        class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
      >
        {{ $t("characters.form.identity") }}
      </h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <div class="flex gap-6">
      <!-- On wide screens the Live Preview card is the portrait uploader, so this
           standalone control only shows when that panel is hidden. -->
      <div class="xl:hidden">
        <AvatarUpload :avatar-url="data.avatarUrl" @change="emit('change', $event)" />
      </div>

      <div class="flex-1 space-y-4">
        <FormField :label="t('characters.form.name')">
          <input
            :value="data.name"
            placeholder="Isolde Fenwick"
            class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
            @input="emit('update:field', 'name', ($event.target as HTMLInputElement).value)"
          />
        </FormField>

        <FormField :label="t('characters.form.title')" :hint="t('characters.form.titleHint')">
          <input
            :value="data.title"
            placeholder="Arcane Librarian of the Sunken Vaults"
            class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
            @input="emit('update:field', 'title', ($event.target as HTMLInputElement).value)"
          />
        </FormField>

        <div class="grid grid-cols-3 gap-3">
          <FormField :label="t('characters.form.species')">
            <Combobox
              :model-value="data.species"
              :options="SPECIES_OPTIONS"
              placeholder="Half-Elf"
              @update:model-value="emit('update:field', 'species', $event)"
            />
          </FormField>
          <FormField :label="t('characters.form.gender')">
            <Combobox
              :model-value="data.gender"
              :options="GENDER_OPTIONS"
              placeholder="Female"
              @update:model-value="emit('update:field', 'gender', $event)"
            />
          </FormField>
          <FormField :label="t('characters.form.age')">
            <input
              :value="data.age"
              placeholder="127"
              class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
              @input="emit('update:field', 'age', ($event.target as HTMLInputElement).value)"
            />
          </FormField>
        </div>
      </div>
    </div>

    <FormField
      :label="t('characters.form.description')"
      :hint="t('characters.form.descriptionHint')"
      :char-count="data.description.length"
      :char-max="12000"
    >
      <AutoTextarea
        :model-value="data.description"
        placeholder="Elara Moonwhisper is a half-elf arcanist who has dedicated her considerable lifespan to preserving the knowledge of the Sunken Library…"
        :min-rows="6"
        :label="t('characters.form.description')"
        @update:model-value="emit('update:field', 'description', $event)"
      />
    </FormField>

    <FormField
      :label="t('characters.form.creatorNotes')"
      :hint="t('characters.form.creatorNotesHint')"
    >
      <AutoTextarea
        :model-value="data.creatorNotes || ''"
        placeholder="A model student makes their parents proud..."
        :min-rows="2"
        :max-vh="35"
        :label="t('characters.form.creatorNotes')"
        @update:model-value="emit('update:field', 'creatorNotes', $event)"
      />
    </FormField>

    <FormField :label="t('characters.form.tags')" :hint="`${data.tags.length}/10`">
      <TagInput
        :tags="data.tags"
        :suggestions="SUGGESTED_TAGS"
        :max="10"
        @add="emit('add:tag', $event)"
        @remove="emit('remove:tag', $event)"
      />
    </FormField>
  </div>
</template>
