<script setup lang="ts">
import type { CharacterData } from "@/types/creator";
import { SPECIES_OPTIONS, GENDER_OPTIONS, SUGGESTED_TAGS } from "@/constants/creatorData";
import FormField from "./FormField.vue";
import Combobox from "./Combobox.vue";
import TagInput from "./TagInput.vue";
import AvatarUpload from "./AvatarUpload.vue";

defineProps<{
  data: CharacterData;
}>();

const emit = defineEmits<{
  "update:field": [field: keyof CharacterData, value: any];
  "add:tag": [tag: string];
  "remove:tag": [tag: string];
}>();
</script>

<template>
  <div class="animate-fade-in-up space-y-6">
    <div>
      <h2 class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Identity</h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <div class="flex gap-6">
      <AvatarUpload :avatar-url="data.avatarUrl" @change="emit('update:field', 'avatarUrl', $event)" />

      <div class="flex-1 space-y-4">
        <FormField label="Name">
          <input
            :value="data.name"
            placeholder="Elara Moonwhisper"
            class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
            @input="emit('update:field', 'name', ($event.target as HTMLInputElement).value)"
          />
        </FormField>

        <FormField label="Title / Subtitle" hint="How they're known">
          <input
            :value="data.title"
            placeholder="Arcane Librarian of the Sunken Vaults"
            class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
            @input="emit('update:field', 'title', ($event.target as HTMLInputElement).value)"
          />
        </FormField>

        <div class="grid grid-cols-3 gap-3">
          <FormField label="Species">
            <Combobox :model-value="data.species" :options="SPECIES_OPTIONS" placeholder="Half-Elf" @update:model-value="emit('update:field', 'species', $event)" />
          </FormField>
          <FormField label="Gender">
            <Combobox :model-value="data.gender" :options="GENDER_OPTIONS" placeholder="Female" @update:model-value="emit('update:field', 'gender', $event)" />
          </FormField>
          <FormField label="Age">
            <input
              :value="data.age"
              placeholder="127"
              class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              @input="emit('update:field', 'age', ($event.target as HTMLInputElement).value)"
            />
          </FormField>
        </div>
      </div>
    </div>

    <FormField label="Tags" :hint="`${data.tags.length}/10`">
      <TagInput :tags="data.tags" :suggestions="SUGGESTED_TAGS" :max="10" @add="emit('add:tag', $event)" @remove="emit('remove:tag', $event)" />
    </FormField>
  </div>
</template>
