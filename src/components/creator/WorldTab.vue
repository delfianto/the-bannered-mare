<script setup lang="ts">
import { ref } from "vue";
import type { CharacterData, LorebookEntry } from "@/types/creator";
import FormField from "./FormField.vue";
import LorebookEntryCard from "./LorebookEntryCard.vue";

defineProps<{
  data: CharacterData;
}>();

const emit = defineEmits<{
  "update:field": [field: keyof CharacterData, value: any];
  addLorebook: [];
  updateLorebook: [id: string, updates: Partial<LorebookEntry>];
  removeLorebook: [id: string];
  export: [];
  import: [data: CharacterData];
}>();

const lorebookOpen = ref(true);
const importRef = ref<HTMLInputElement | null>(null);

function handleImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    try {
      const parsed = JSON.parse(ev.target?.result as string);
      if (parsed.name) emit("import", parsed);
    } catch { /* ignore */ }
  };
  reader.readAsText(file);
  (e.target as HTMLInputElement).value = "";
}
</script>

<template>
  <div class="animate-fade-in-up space-y-6">
    <div>
      <h2 class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">World Setting</h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <FormField label="Scenario" hint="Starting situation / context" :char-count="data.scenario.length" :char-max="2000">
      <textarea
        :value="data.scenario"
        placeholder="You have descended into the ruins beneath the coastal city of Thornhaven, following rumors of the legendary Sunken Library…"
        rows="4"
        class="w-full resize-y rounded-lg border bg-muted/40 px-4 py-3 text-sm leading-relaxed text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update:field', 'scenario', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <!-- Lorebook -->
    <div>
      <button
        type="button"
        class="flex w-full items-center gap-2 border-b py-2 text-sm font-medium text-foreground transition-colors hover:text-primary"
        @click="lorebookOpen = !lorebookOpen"
      >
        <UIcon name="i-lucide-chevron-right" class="h-4 w-4 transition-transform" :class="lorebookOpen ? 'rotate-90' : ''" />
        <UIcon name="i-lucide-book-open" class="h-3.5 w-3.5" />
        <span class="font-cinzel text-[11px] uppercase tracking-[0.08em]">Lorebook / World Info</span>
        <span class="ml-auto text-xs text-muted-foreground">
          {{ data.lorebook.length }} {{ data.lorebook.length === 1 ? 'entry' : 'entries' }}
        </span>
      </button>

      <div v-if="lorebookOpen" class="space-y-3 pt-4">
        <LorebookEntryCard
          v-for="(entry, i) in data.lorebook"
          :key="entry.id"
          :entry="entry"
          :index="i"
          @update="(id: string, updates: Partial<LorebookEntry>) => emit('updateLorebook', id, updates)"
          @remove="(id: string) => emit('removeLorebook', id)"
        />

        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-3 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
          @click="emit('addLorebook')"
        >
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Add Lorebook Entry
        </button>
      </div>
    </div>

    <!-- Import / Export -->
    <div>
      <h2 class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Import / Export</h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <div class="grid grid-cols-2 gap-3">
      <button
        type="button"
        class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-5 transition-all hover:border-primary/40 hover:bg-accent/30"
        @click="importRef?.click()"
      >
        <UIcon name="i-lucide-upload" class="h-5 w-5 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">Import Character</span>
        <span class="text-[11px] text-muted-foreground">.json or TavernAI card</span>
        <input ref="importRef" type="file" accept=".json,.png" class="hidden" @change="handleImport" />
      </button>

      <button
        type="button"
        class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-5 transition-all hover:border-primary/40 hover:bg-accent/30"
        @click="emit('export')"
      >
        <UIcon name="i-lucide-download" class="h-5 w-5 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">Export as JSON</span>
        <span class="text-[11px] text-muted-foreground">TavernAI v2 compatible</span>
      </button>
    </div>
  </div>
</template>
