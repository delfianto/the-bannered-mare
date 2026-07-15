<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useChatLlmLogs, type LlmAuditLog } from "@/composables/useChatLlmLogs";
import { useCompletionSignal } from "@/composables/useCompletionSignal";
import {
  formatTokens,
  formatLatency,
  formatCost,
  formatJson,
  formatLogTime as fmtLogTime,
} from "@/utils/formatLog";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";
import AppTooltip from "@/components/shared/AppTooltip.vue";

const props = defineProps<{ chatId?: string }>();

const { t } = useI18n();

// This conversation's LLM audit records. The composable caches by chat id.
const { logs, loading: logsLoading, error: logsError, load: loadLogs } = useChatLlmLogs();

watch(
  () => props.chatId,
  (id) => {
    if (id) void loadLogs(id);
  },
  { immediate: true },
);

function refreshLogs() {
  if (props.chatId) void loadLogs(props.chatId, true);
}

// A model call for this chat settling refreshes the (visible) Logs tab. This tab
// only exists while active, so remounting already refetches for the hidden case.
const completionSignal = useCompletionSignal();
watch(completionSignal.tick, () => {
  if (completionSignal.chatId.value === props.chatId) refreshLogs();
});

// Newest first, regardless of the order the API hands them back.
const sortedLogs = computed(() =>
  logs.value.slice().sort((a, b) => b.created_at.localeCompare(a.created_at)),
);

// Per-row expansion for the (lazily stringified) request/response payloads.
const expandedLogs = ref<Record<string, boolean>>({});

function toggleLog(id: string) {
  expandedLogs.value[id] = !expandedLogs.value[id];
}

function isErrorLog(log: LlmAuditLog): boolean {
  return log.status.toLowerCase() !== "success" || !!log.error_message;
}

function formatLogTime(iso: string): string {
  return fmtLogTime(iso, t);
}
</script>

<template>
  <div class="p-4">
    <div class="mb-3 flex items-center justify-between">
      <span
        class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
      >
        {{ $t("chat.drawer.tabs.logs") }}
      </span>
      <AppTooltip :text="$t('chat.drawer.logsRefresh')" side="left">
        <button
          class="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-base-300/40 hover:text-foreground disabled:opacity-50"
          :disabled="logsLoading"
          :aria-label="$t('chat.drawer.logsRefresh')"
          @click="refreshLogs"
        >
          <AppIcon
            name="i-lucide-refresh-cw"
            class="size-3.5"
            :class="{ 'animate-spin': logsLoading && sortedLogs.length }"
          />
        </button>
      </AppTooltip>
    </div>

    <!-- Full spinner only on the first fetch; a background refresh keeps
         the current rows on screen (the button icon spins instead). -->
    <div v-if="logsLoading && !sortedLogs.length" class="flex justify-center py-12">
      <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="logsError" class="py-12 text-center text-xs text-muted-foreground">
      {{ $t("chat.drawer.logsError") }}
    </div>

    <div v-else-if="sortedLogs.length" class="space-y-2">
      <div
        v-for="log in sortedLogs"
        :key="log.id"
        class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40"
      >
        <!-- Summary row -->
        <button
          class="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-base-300/40"
          @click="toggleLog(log.id)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="min-w-0 truncate text-sm font-medium text-foreground">
                {{ log.model }}
              </span>
              <span
                class="shrink-0 rounded-full px-2 py-0.5 text-3xs font-medium tracking-wide uppercase"
                :class="isErrorLog(log) ? 'bg-error/15 text-error' : 'bg-success/15 text-success'"
              >
                {{
                  isErrorLog(log)
                    ? $t("chat.drawer.logsStatusError")
                    : $t("chat.drawer.logsStatusSuccess")
                }}
              </span>
            </div>
            <p class="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-2xs text-muted-foreground">
              <span>{{ log.provider }}</span>
              <span class="text-muted-foreground/40">·</span>
              <span>{{ formatLogTime(log.created_at) }}</span>
            </p>
          </div>
          <AppIcon
            name="i-lucide-chevron-down"
            class="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform"
            :class="{ 'rotate-180': expandedLogs[log.id] }"
          />
        </button>

        <!-- Metrics -->
        <div
          class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/40 px-4 py-2 text-2xs text-muted-foreground"
        >
          <span class="flex items-center gap-1">
            <AppIcon name="i-lucide-hash" class="size-3 text-muted-foreground/60" />
            {{ $t("chat.drawer.logsTokens") }}:
            <span class="tabular-nums text-foreground">
              {{ formatTokens(log.prompt_tokens) }} →
              {{ formatTokens(log.completion_tokens) }}
            </span>
            <span class="text-muted-foreground/50"> ({{ formatTokens(log.total_tokens) }}) </span>
          </span>
          <span class="flex items-center gap-1">
            <AppIcon name="i-lucide-timer" class="size-3 text-muted-foreground/60" />
            <span class="tabular-nums text-foreground">{{ formatLatency(log.latency_ms) }}</span>
          </span>
          <span v-if="formatCost(log.estimated_cost_usd)" class="flex items-center gap-1">
            <AppIcon name="i-lucide-coins" class="size-3 text-muted-foreground/60" />
            <span class="tabular-nums text-foreground">{{
              formatCost(log.estimated_cost_usd)
            }}</span>
          </span>
        </div>

        <!-- Error message -->
        <p
          v-if="log.error_message"
          class="border-t border-border/40 px-4 py-2 text-2xs leading-snug text-error"
        >
          {{ log.error_message }}
        </p>

        <!-- Expandable payloads (stringified only when open) -->
        <div v-if="expandedLogs[log.id]" class="space-y-2 border-t border-border/40 p-3">
          <CollapsibleField
            :label="$t('chat.drawer.logsRequest')"
            :content="formatJson(log.request_payload)"
            mono
          />
          <CollapsibleField
            :label="$t('chat.drawer.logsResponse')"
            :content="formatJson(log.response_payload)"
            mono
          />
        </div>
      </div>
    </div>

    <p v-else class="py-8 text-center text-xs text-muted-foreground/70">
      {{ $t("chat.drawer.logsEmpty") }}
    </p>
  </div>
</template>
