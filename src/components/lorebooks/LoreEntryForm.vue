<script setup lang="ts">
import { ref, watch } from "vue";
import type { LoreEntryResponse, LoreEntryCreate } from "@/composables/useLorebooks";
import type { components } from "@/api/schema";

type InsertionPosition = components["schemas"]["InsertionPosition"];

const props = defineProps<{
  initial?: LoreEntryResponse | null;
  saving?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: LoreEntryCreate];
  cancel: [];
}>();

const name = ref("");
const content = ref("");
const keysText = ref("");
const enabled = ref(true);
const constant = ref(false);
const position = ref<InsertionPosition>("after_character");
const priority = ref(100);
const order = ref(0);

// Advanced matching fields aren't surfaced in this form but are preserved
// across edits (and sensibly defaulted on create).
const carried = ref({
  secondary_keys: [] as string[],
  secondary_logic: "and_any" as components["schemas"]["SecondaryLogic"],
  case_sensitive: false,
  match_whole_words: false,
  use_regex: false,
  depth: 4,
  role: "system" as components["schemas"]["MessageRole"],
  scan_depth: null as number | null,
  ignore_budget: false,
});

watch(
  () => props.initial,
  (e) => {
    name.value = e?.name ?? "";
    content.value = e?.content ?? "";
    keysText.value = e?.keys?.join(", ") ?? "";
    enabled.value = e?.enabled ?? true;
    constant.value = e?.constant ?? false;
    position.value = e?.position ?? "after_character";
    priority.value = e?.priority ?? 100;
    order.value = e?.order ?? 0;
    if (e) {
      carried.value = {
        secondary_keys: e.secondary_keys ?? [],
        secondary_logic: e.secondary_logic,
        case_sensitive: e.case_sensitive,
        match_whole_words: e.match_whole_words,
        use_regex: e.use_regex,
        depth: e.depth,
        role: e.role,
        scan_depth: e.scan_depth ?? null,
        ignore_budget: e.ignore_budget,
      };
    }
  },
  { immediate: true },
);

const positions: { value: InsertionPosition; label: string }[] = [
  { value: "before_character", label: "Before character" },
  { value: "after_character", label: "After character" },
  { value: "at_depth", label: "At depth" },
  { value: "before_examples", label: "Before examples" },
];

function onSubmit() {
  if (!name.value.trim() || !content.value.trim()) return;
  const keys = keysText.value
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
  emit("submit", {
    name: name.value.trim(),
    content: content.value.trim(),
    keys,
    enabled: enabled.value,
    constant: constant.value,
    position: position.value,
    priority: priority.value,
    order: order.value,
    ...carried.value,
  });
}
</script>

<template>
  <div class="animate-fade-in-up rounded-xl border bg-card/50 p-6">
    <h3 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
      {{ initial ? $t('lorebooks.entryForm.editTitle') : $t('lorebooks.entryForm.newTitle') }}
    </h3>

    <div class="space-y-4">
      <label class="block">
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.name') }}</span>
        <input
          v-model="name"
          type="text"
          :placeholder="$t('lorebooks.entryForm.namePlaceholder')"
          class="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </label>

      <label class="block">
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.keys') }}</span>
        <input
          v-model="keysText"
          type="text"
          :placeholder="$t('lorebooks.entryForm.keysPlaceholder')"
          class="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </label>

      <label class="block">
        <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.content') }}</span>
        <textarea
          v-model="content"
          rows="4"
          :placeholder="$t('lorebooks.entryForm.contentPlaceholder')"
          class="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </label>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.position') }}</span>
          <select
            v-model="position"
            class="h-[38px] w-full rounded-lg border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option v-for="p in positions" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.order') }}</span>
          <input
            v-model.number="order"
            type="number"
            class="h-[38px] w-full rounded-lg border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.entryForm.priority') }}</span>
          <input
            v-model.number="priority"
            type="number"
            class="h-[38px] w-full rounded-lg border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </label>
      </div>

      <div class="flex flex-wrap gap-3">
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2"
          role="switch"
          :aria-checked="enabled"
          @click="enabled = !enabled"
        >
          <span
            class="flex h-[20px] w-9 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="enabled ? 'bg-primary' : 'bg-muted-foreground/40'"
          >
            <span
              class="h-3.5 w-3.5 rounded-full shadow-sm transition-transform duration-300"
              :class="enabled ? 'translate-x-[14px] bg-background' : 'translate-x-0 bg-white'"
            />
          </span>
          <span class="text-sm text-foreground">{{ $t('lorebooks.entryForm.enabled') }}</span>
        </button>

        <button
          type="button"
          class="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2"
          role="switch"
          :aria-checked="constant"
          @click="constant = !constant"
        >
          <span
            class="flex h-[20px] w-9 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="constant ? 'bg-primary' : 'bg-muted-foreground/40'"
          >
            <span
              class="h-3.5 w-3.5 rounded-full shadow-sm transition-transform duration-300"
              :class="constant ? 'translate-x-[14px] bg-background' : 'translate-x-0 bg-white'"
            />
          </span>
          <span class="text-sm text-foreground">{{ $t('lorebooks.entryForm.constant') }}</span>
        </button>
      </div>

      <div class="flex items-center gap-3 pt-1">
        <button
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          :disabled="saving || !name.trim() || !content.trim()"
          @click="onSubmit"
        >
          {{ initial ? $t('lorebooks.entryForm.save') : $t('lorebooks.entryForm.add') }}
        </button>
        <button
          class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="$emit('cancel')"
        >
          {{ $t('common.cancel') }}
        </button>
      </div>
    </div>
  </div>
</template>
