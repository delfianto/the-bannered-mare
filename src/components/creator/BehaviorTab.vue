<script setup lang="ts">
import { ref } from "vue";
import type { CharacterData } from "@/types/creator";
import { RESPONSE_STYLE_OPTIONS } from "@/constants/creatorData";
import FormField from "./FormField.vue";
import Combobox from "./Combobox.vue";
import DialoguePairEditor from "./DialoguePairEditor.vue";

defineProps<{
  data: CharacterData;
}>();

const emit = defineEmits<{
  "update:field": [field: keyof CharacterData, value: any];
  addDialogue: [];
  updateDialogue: [id: string, field: "userMessage" | "characterReply", value: string];
  removeDialogue: [id: string];
}>();

const dialoguesOpen = ref(true);
</script>

<template>
  <div class="animate-fade-in-up space-y-6">
    <div>
      <h2 class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Persona</h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <FormField label="Description" hint="Backstory, traits, motivations" :char-count="data.description.length" :char-max="12000">
      <textarea
        :value="data.description"
        placeholder="Elara Moonwhisper is a half-elf arcanist who has dedicated her considerable lifespan to preserving the knowledge of the Sunken Library\u2026"
        rows="6"
        class="w-full resize-y rounded-lg border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update:field', 'description', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <FormField label="Personality Summary" :char-count="data.personality.length" :char-max="1000">
      <textarea
        :value="data.personality"
        placeholder="Intellectual and warm, with a dry wit. Treats books like old friends and adventurers like puzzles."
        rows="3"
        class="w-full resize-y rounded-lg border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update:field', 'personality', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <FormField label="Greeting" hint="First message when a session begins" :char-count="data.greeting.length" :char-max="4000">
      <textarea
        :value="data.greeting"
        :placeholder="'*The torchlight flickers against the damp stone walls.* &quot;These wards were placed here centuries ago\u2026&quot;'"
        rows="4"
        class="w-full resize-y rounded-lg border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update:field', 'greeting', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <FormField label="Response Style">
      <Combobox :model-value="data.responseStyle" :options="RESPONSE_STYLE_OPTIONS" placeholder="Narrative" @update:model-value="emit('update:field', 'responseStyle', $event)" />
    </FormField>

    <!-- Example Dialogues -->
    <div>
      <button
        type="button"
        class="flex w-full items-center gap-2 border-b py-2 text-sm font-medium text-foreground transition-colors hover:text-primary"
        @click="dialoguesOpen = !dialoguesOpen"
      >
        <UIcon name="i-lucide-chevron-right" class="h-4 w-4 transition-transform" :class="dialoguesOpen ? 'rotate-90' : ''" />
        <span class="font-cinzel text-[11px] uppercase tracking-[0.08em]">Example Dialogues</span>
        <span class="ml-auto text-xs text-muted-foreground">
          {{ data.exampleDialogues.length }} {{ data.exampleDialogues.length === 1 ? 'exchange' : 'exchanges' }}
        </span>
      </button>

      <div v-if="dialoguesOpen" class="space-y-3 pt-4">
        <DialoguePairEditor
          v-for="(pair, i) in data.exampleDialogues"
          :key="pair.id"
          :pair="pair"
          :index="i"
          @update="(id: string, field: 'userMessage' | 'characterReply', val: string) => emit('updateDialogue', id, field, val)"
          @remove="(id: string) => emit('removeDialogue', id)"
        />

        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-3 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
          @click="emit('addDialogue')"
        >
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Add Dialogue Exchange
        </button>
      </div>
    </div>
  </div>
</template>
