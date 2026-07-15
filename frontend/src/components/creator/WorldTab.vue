<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { CharacterData, LorebookEntry } from "@/types/creator";
import FormField from "./FormField.vue";
import LorebookEntryCard from "./LorebookEntryCard.vue";
import AutoTextarea from "./AutoTextarea.vue";

const { t } = useI18n();

defineProps<{
  data: CharacterData;
}>();

const emit = defineEmits<{
  "update:field": [field: keyof CharacterData, value: CharacterData[keyof CharacterData]];
  addLorebook: [];
  updateLorebook: [id: string, updates: Partial<LorebookEntry>];
  removeLorebook: [id: string];
  export: [];
  import: [data: CharacterData];
}>();

const lorebookOpen = ref(true);
const advancedOpen = ref(false);
const importRef = ref<HTMLInputElement | null>(null);

function handleImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    try {
      const parsed = JSON.parse(ev.target?.result as string);
      if (parsed.name) emit("import", parsed);
    } catch {
      /* ignore */
    }
  };
  reader.readAsText(file);
  (e.target as HTMLInputElement).value = "";
}
</script>

<template>
  <div class="animate-fade-in-up space-y-6">
    <div>
      <h2
        class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
      >
        {{ $t("characters.form.worldSetting") }}
      </h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <FormField
      :label="t('characters.form.scenario')"
      :hint="t('characters.form.scenarioHint')"
      :char-count="data.scenario.length"
      :char-max="2000"
    >
      <AutoTextarea
        :model-value="data.scenario"
        placeholder="You have descended into the ruins beneath the coastal city of Thornhaven, following rumors of the legendary Sunken Library…"
        :min-rows="4"
        :label="t('characters.form.scenario')"
        @update:model-value="emit('update:field', 'scenario', $event)"
      />
    </FormField>

    <!-- Lorebook -->
    <div>
      <button
        type="button"
        class="flex w-full items-center gap-2 border-b py-2 text-sm font-medium text-foreground transition-colors hover:text-primary"
        @click="lorebookOpen = !lorebookOpen"
      >
        <AppIcon
          name="i-lucide-chevron-right"
          class="size-4 transition-transform"
          :class="lorebookOpen ? 'rotate-90' : ''"
        />
        <AppIcon name="i-lucide-book-open" class="size-3.5" />
        <span class="font-cinzel text-2xs tracking-[0.08em] uppercase">{{
          $t("characters.form.lorebook")
        }}</span>
        <span class="ml-auto text-xs text-muted-foreground">
          {{ data.lorebook.length }}
          {{
            data.lorebook.length === 1
              ? t("characters.form.entry").split(" | ")[0]
              : t("characters.form.entry").split(" | ")[1]
          }}
        </span>
      </button>

      <div v-if="lorebookOpen" class="space-y-3 pt-4">
        <LorebookEntryCard
          v-for="(entry, i) in data.lorebook"
          :key="entry.id"
          :entry="entry"
          :index="i"
          @update="
            (id: string, updates: Partial<LorebookEntry>) => emit('updateLorebook', id, updates)
          "
          @remove="(id: string) => emit('removeLorebook', id)"
        />

        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-3 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
          @click="emit('addLorebook')"
        >
          <AppIcon name="i-lucide-plus" class="size-4" />
          {{ $t("characters.form.addLorebook") }}
        </button>
      </div>
    </div>

    <!-- Advanced — power-user overrides, collapsed by default so they don't
         clutter the common path. -->
    <div>
      <button
        type="button"
        class="flex w-full items-center gap-2 border-b py-2 text-sm font-medium text-foreground transition-colors hover:text-primary"
        @click="advancedOpen = !advancedOpen"
      >
        <AppIcon
          name="i-lucide-chevron-right"
          class="size-4 transition-transform"
          :class="advancedOpen ? 'rotate-90' : ''"
        />
        <AppIcon name="i-lucide-sliders-horizontal" class="size-3.5" />
        <span class="font-cinzel text-2xs tracking-[0.08em] uppercase">{{
          $t("characters.form.advanced")
        }}</span>
      </button>

      <div v-if="advancedOpen" class="pt-4">
        <FormField
          :label="t('characters.form.systemPrompt')"
          :hint="t('characters.form.systemPromptHint')"
          :char-count="data.systemPrompt?.length || 0"
          :char-max="12000"
        >
          <AutoTextarea
            :model-value="data.systemPrompt || ''"
            placeholder="Custom system instructions for the LLM behavior…"
            :min-rows="4"
            :label="t('characters.form.systemPrompt')"
            @update:model-value="emit('update:field', 'systemPrompt', $event)"
          />
        </FormField>
      </div>
    </div>

    <!-- Import / Export -->
    <div>
      <h2
        class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
      >
        {{ $t("characters.form.importExport") }}
      </h2>
      <div class="mt-2 h-px bg-border" />
    </div>

    <div class="grid grid-cols-2 gap-3">
      <button
        type="button"
        class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-5 transition-all hover:border-primary/40 hover:bg-base-300/30"
        @click="importRef?.click()"
      >
        <AppIcon name="i-lucide-upload" class="size-5 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">{{
          $t("characters.form.importCharacter")
        }}</span>
        <span class="text-2xs text-muted-foreground">{{
          $t("characters.form.importFileTypes")
        }}</span>
        <input
          ref="importRef"
          type="file"
          accept=".json,.png"
          class="hidden"
          @change="handleImport"
        />
      </button>

      <button
        type="button"
        class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-5 transition-all hover:border-primary/40 hover:bg-base-300/30"
        @click="emit('export')"
      >
        <AppIcon name="i-lucide-download" class="size-5 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">{{
          $t("characters.form.exportJson")
        }}</span>
        <span class="text-2xs text-muted-foreground">{{
          $t("characters.form.exportFileType")
        }}</span>
      </button>
    </div>
  </div>
</template>
