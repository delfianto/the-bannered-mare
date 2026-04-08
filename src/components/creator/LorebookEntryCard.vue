<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { LorebookEntry } from "@/types/creator";

const { t } = useI18n();

const props = defineProps<{
  entry: LorebookEntry;
  index: number;
}>();

const emit = defineEmits<{
  update: [id: string, updates: Partial<LorebookEntry>];
  remove: [id: string];
}>();

const expanded = ref(true);
const keywordInput = ref("");

function addKeyword() {
  const kw = keywordInput.value.trim();
  if (!kw || props.entry.keywords.includes(kw)) return;
  emit("update", props.entry.id, { keywords: [...props.entry.keywords, kw] });
  keywordInput.value = "";
}

function removeKeyword(kw: string) {
  emit("update", props.entry.id, { keywords: props.entry.keywords.filter((k) => k !== kw) });
}
</script>

<template>
  <div
    class="overflow-hidden rounded-xl border transition-colors"
    :class="entry.enabled ? 'border-border bg-muted/20' : 'border-border/50 bg-muted/10 opacity-60'"
  >
    <!-- Header -->
    <div class="flex items-center gap-2 px-4 py-3">
      <button type="button" class="text-muted-foreground transition-colors hover:text-foreground" :aria-label="expanded ? 'Collapse entry' : 'Expand entry'" @click="expanded = !expanded">
        <UIcon name="i-lucide-chevron-down" class="h-4 w-4 transition-transform" :class="expanded ? 'rotate-180' : ''" />
      </button>

      <span class="text-xs font-medium text-muted-foreground">Entry #{{ index + 1 }}</span>

      <div v-if="entry.keywords.length > 0" class="ml-2 flex items-center gap-1">
        <span
          v-for="kw in entry.keywords.slice(0, 3)"
          :key="kw"
          class="rounded-full bg-accent px-2 py-0.5 text-[10px] font-medium text-accent-foreground"
        >
          {{ kw }}
        </span>
        <span v-if="entry.keywords.length > 3" class="text-[10px] text-muted-foreground">
          +{{ entry.keywords.length - 3 }}
        </span>
      </div>

      <div class="ml-auto flex items-center gap-1">
        <button
          type="button"
          :title="entry.enabled ? 'Disable' : 'Enable'"
          :aria-label="entry.enabled ? 'Disable entry' : 'Enable entry'"
          class="flex h-7 w-7 items-center justify-center rounded-md transition-colors"
          :class="entry.enabled ? 'text-primary hover:bg-primary/10' : 'text-muted-foreground hover:bg-accent'"
          @click="emit('update', entry.id, { enabled: !entry.enabled })"
        >
          <UIcon name="i-lucide-power" class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          :aria-label="t('characters.form.removeLorebook')"
          @click="emit('remove', entry.id)"
        >
          <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- Content -->
    <div v-if="expanded" class="space-y-3 px-4 pb-4">
      <label class="block space-y-1.5">
        <span class="text-xs font-medium text-muted-foreground">{{ t('characters.form.keywords') }}</span>
        <div class="flex min-h-[36px] flex-wrap items-center gap-1.5 rounded-lg border bg-background p-2">
          <span
            v-for="kw in entry.keywords"
            :key="kw"
            class="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/15 px-2 py-0.5 text-[11px] font-medium text-primary"
          >
            {{ kw }}
            <button type="button" class="hover:text-destructive" :aria-label="t('characters.form.removeKeyword', { keyword: kw })" @click="removeKeyword(kw)">
              <UIcon name="i-lucide-x" class="h-2.5 w-2.5" />
            </button>
          </span>
          <input
            v-model="keywordInput"
            :placeholder="t('characters.form.addKeywordPlaceholder')"
            class="min-w-[60px] flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
            @keydown.enter.prevent="addKeyword"
          />
        </div>
      </label>

      <label class="block space-y-1.5">
        <div class="flex justify-between">
          <span class="text-xs font-medium text-muted-foreground">{{ t('characters.form.content') }}</span>
          <span class="text-[10px] text-muted-foreground">{{ entry.content.length }}/2000</span>
        </div>
        <textarea
          :value="entry.content"
          placeholder="The Sunken Library was once the greatest repository of arcane knowledge…"
          rows="3"
          class="w-full resize-y rounded-lg border bg-background px-3 py-2.5 text-sm leading-relaxed text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
          @input="emit('update', entry.id, { content: ($event.target as HTMLTextAreaElement).value })"
        />
      </label>
    </div>
  </div>
</template>
