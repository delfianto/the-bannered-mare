<script setup lang="ts">
import { computed, watch } from "vue";
import { useChatPromptPreview } from "@/composables/useChatPromptPreview";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";

const props = defineProps<{ chatId?: string }>();

// Resolved prompt scaffolding + effective params. The composable caches by chat
// id, so this only hits the network the first time a given chat is previewed.
const {
  preview,
  loading: previewLoading,
  error: previewError,
  load: loadPreview,
} = useChatPromptPreview();

watch(
  () => props.chatId,
  (id) => {
    if (id) void loadPreview(id);
  },
  { immediate: true },
);

// Effective sampler params as a sorted key/value list; objects/arrays render as
// compact JSON, scalars plainly.
const paramEntries = computed(() => {
  const params = preview.value?.parameters ?? {};
  return Object.keys(params)
    .sort()
    .map((key) => ({ key, value: formatParamValue(params[key]) }));
});

function formatParamValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function roleLabel(role: string): string {
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : role;
}
</script>

<template>
  <div class="p-4">
    <div v-if="previewLoading && !preview" class="flex justify-center py-12">
      <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="previewError" class="py-12 text-center text-xs text-muted-foreground">
      {{ $t("chat.drawer.sessionError") }}
    </div>

    <div v-else-if="preview" class="space-y-4">
      <!-- Resolved model -->
      <div class="rounded-xl border bg-base-100/50 p-4">
        <h3 class="text-base font-semibold text-foreground">
          {{ preview.model_display_name || $t("chat.drawer.sessionModelUnknown") }}
        </h3>
        <p
          v-if="preview.provider_name || preview.model_identifier"
          class="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground"
        >
          <span v-if="preview.provider_name">{{ preview.provider_name }}</span>
          <span
            v-if="preview.provider_name && preview.model_identifier"
            class="text-muted-foreground/40"
            >·</span
          >
          <span v-if="preview.model_identifier" class="font-mono text-muted-foreground/80">
            {{ preview.model_identifier }}
          </span>
        </p>
      </div>

      <!-- Effective parameters -->
      <div>
        <h4
          class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ $t("chat.drawer.sessionParameters") }}
        </h4>
        <dl
          v-if="paramEntries.length"
          class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40"
        >
          <div
            v-for="(entry, i) in paramEntries"
            :key="entry.key"
            class="flex items-start justify-between gap-3 px-3 py-2"
            :class="i > 0 ? 'border-t border-border/40' : ''"
          >
            <dt class="shrink-0 text-xs text-muted-foreground">{{ entry.key }}</dt>
            <dd class="min-w-0 text-right font-mono text-xs break-words text-foreground">
              {{ entry.value }}
            </dd>
          </div>
        </dl>
        <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
          {{ $t("chat.drawer.sessionParametersEmpty") }}
        </p>
      </div>

      <!-- Assembled prompt scaffolding -->
      <div>
        <h4
          class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ $t("chat.drawer.sessionPrompt") }}
        </h4>
        <div v-if="preview.messages.length" class="space-y-2">
          <CollapsibleField
            v-for="(msg, i) in preview.messages"
            :key="i"
            :label="roleLabel(msg.role)"
            :content="msg.content"
            mono
          />
        </div>
        <p v-else class="px-1 py-2 text-xs text-muted-foreground/70">
          {{ $t("chat.drawer.sessionPromptEmpty") }}
        </p>
      </div>
    </div>
  </div>
</template>
