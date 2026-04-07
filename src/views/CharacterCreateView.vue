<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useCharacterForm } from "@/composables/useCharacterForm";
import { SAMPLE_CHARACTER } from "@/constants/creatorData";
import CharacterTab from "@/components/creator/CharacterTab.vue";
import BehaviorTab from "@/components/creator/BehaviorTab.vue";
import WorldTab from "@/components/creator/WorldTab.vue";
import CharacterPreview from "@/components/creator/CharacterPreview.vue";
import type { CreatorTab, CharacterData } from "@/types/creator";

const router = useRouter();
const activeTab = ref<CreatorTab>("character");
const saved = ref(false);

const form = useCharacterForm(SAMPLE_CHARACTER as Partial<CharacterData>);

const tabs: { id: CreatorTab; label: string; icon: string }[] = [
  { id: "character", label: "Character", icon: "i-lucide-user" },
  { id: "behavior", label: "Behavior", icon: "i-lucide-brain" },
  { id: "world", label: "World", icon: "i-lucide-globe" },
];

function handleSave() {
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
}

function handleExport() {
  const json = JSON.stringify(form.data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${form.data.name || "character"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function handleImport(data: CharacterData) {
  form.loadCharacter(data);
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <button
          class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="router.back()"
        >
          <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
            <UIcon name="i-lucide-flame" class="h-3.5 w-3.5 text-primary-foreground" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            Create Character
          </h1>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          class="flex h-9 items-center gap-2 rounded-lg border border-border px-4 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          @click="handleExport"
        >
          <UIcon name="i-lucide-download" class="h-4 w-4" />
          Export
        </button>
        <button
          class="flex h-9 items-center gap-2 rounded-lg px-5 text-sm font-medium transition-all active:scale-[0.96]"
          :class="!saved ? 'bg-primary text-primary-foreground shadow-sm hover:shadow-[0_2px_12px_var(--color-primary)/0.3]' : 'bg-muted text-muted-foreground'"
          @click="handleSave"
        >
          <UIcon name="i-lucide-save" class="h-4 w-4" />
          Save
        </button>
      </div>
    </header>

    <!-- Tab Nav -->
    <div class="flex-shrink-0 border-b border-border bg-background/60">
      <div class="flex items-center gap-1 px-8">
        <div class="mx-auto flex max-w-[580px] items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
          :class="activeTab === tab.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = tab.id"
        >
          <UIcon :name="tab.icon" class="h-4 w-4" />
          <span style="letter-spacing: 0.03em">{{ tab.label }}</span>
          <span
            v-if="activeTab === tab.id"
            class="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-primary transition-all"
          />
        </button>
        </div>
      </div>
    </div>

    <!-- Content: Form + Preview -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Form Panel -->
      <div class="flex-1 overflow-y-auto px-8 py-6" style="min-width: 0">
        <div class="mx-auto max-w-[580px]">
          <CharacterTab
            v-if="activeTab === 'character'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add:tag="form.addTag"
            @remove:tag="form.removeTag"
          />
          <BehaviorTab
            v-if="activeTab === 'behavior'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add-dialogue="form.addDialogue"
            @update-dialogue="form.updateDialogue"
            @remove-dialogue="form.removeDialogue"
          />
          <WorldTab
            v-if="activeTab === 'world'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add-lorebook="form.addLorebook"
            @update-lorebook="form.updateLorebook"
            @remove-lorebook="form.removeLorebook"
            @export="handleExport"
            @import="handleImport"
          />
        </div>
      </div>

      <!-- Preview Panel -->
      <div class="hidden w-[340px] min-w-[340px] overflow-y-auto border-l border-border bg-secondary/30 px-5 py-6 xl:block">
        <div class="sticky top-0">
          <p class="mb-4 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            Live Preview
          </p>
          <CharacterPreview :data="form.data" :completeness="form.completeness.value" />
        </div>
      </div>
    </div>
  </div>
</template>
