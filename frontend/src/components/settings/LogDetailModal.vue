<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import Modal from "@/components/shared/Modal.vue";
import type { components } from "@/api/schema";

type HttpLog = components["schemas"]["HttpLogResponse"];
type LlmLog = components["schemas"]["LlmAuditLogResponse"];
type ErrorLog = components["schemas"]["ErrorLogResponse"];
type LogKind = "http" | "llm" | "error";

const { t } = useI18n();

const props = defineProps<{
  show: boolean;
  kind: LogKind | null;
  log: HttpLog | LlmLog | ErrorLog | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const httpLog = computed(() => (props.kind === "http" ? (props.log as HttpLog) : null));
const llmLog = computed(() => (props.kind === "llm" ? (props.log as LlmLog) : null));
const errLog = computed(() => (props.kind === "error" ? (props.log as ErrorLog) : null));

const title = computed(() => {
  if (props.kind === "http") return t("settings.logs.httpDetails");
  if (props.kind === "llm") return t("settings.logs.llmDetails");
  if (props.kind === "error") return t("settings.logs.errorDetails");
  return "";
});

// Request messages, typed loosely since the backend stores them as free-form dicts.
const requestMessages = computed(() => {
  const payload = llmLog.value?.request_payload ?? [];
  return payload.map((m) => ({
    role: typeof m.role === "string" ? m.role : "unknown",
    content: typeof m.content === "string" ? m.content : JSON.stringify(m.content, null, 2),
  }));
});

const responsePayload = computed(() => llmLog.value?.response_payload ?? null);
const responseContent = computed(() => {
  const c = responsePayload.value?.content;
  return typeof c === "string" ? c : null;
});
const responseReasoning = computed(() => {
  const r = responsePayload.value?.reasoning ?? responsePayload.value?.reasoning_content;
  return typeof r === "string" ? r : null;
});
const responseMeta = computed(() => {
  if (!responsePayload.value) return null;
  const {
    content: _content,
    reasoning: _r,
    reasoning_content: _rc,
    ...rest
  } = responsePayload.value as Record<string, unknown>;
  return rest;
});

const roleColors: Record<string, string> = {
  system: "bg-base-300 text-muted-foreground",
  user: "bg-blue-500/10 text-blue-500",
  assistant: "bg-primary/10 text-primary",
};

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

const copiedKey = ref<string | null>(null);
async function copy(text: string, key: string) {
  try {
    await navigator.clipboard.writeText(text);
    copiedKey.value = key;
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = null;
    }, 1500);
  } catch {
    // clipboard unavailable — ignore
  }
}

function formatFullTimestamp(iso: string): string {
  return new Date(iso).toLocaleString();
}
</script>

<template>
  <Modal :show="show" :title="title" max-width="3xl" @close="emit('close')">
    <div v-if="httpLog" class="space-y-4">
      <!-- Meta -->
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
        <span class="font-mono text-foreground">{{ httpLog.method }} {{ httpLog.path }}</span>
        <span>{{ httpLog.status_code }}</span>
        <span>{{ httpLog.latency_ms.toFixed(0) }}ms</span>
        <span v-if="httpLog.client_ip">{{ httpLog.client_ip }}</span>
        <span>{{ formatFullTimestamp(httpLog.created_at) }}</span>
        <span class="font-mono text-[0.625rem] text-muted-foreground/60">{{
          httpLog.request_id
        }}</span>
      </div>
      <p v-if="httpLog.user_agent" class="truncate text-xs text-muted-foreground/70">
        {{ httpLog.user_agent }}
      </p>

      <!-- Request Body -->
      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <h3 class="text-xs font-semibold tracking-wide text-foreground uppercase">
            {{ $t("settings.logs.requestBody") }}
          </h3>
          <button
            v-if="httpLog.request_body"
            class="text-[0.6875rem] text-muted-foreground hover:text-foreground"
            @click="copy(prettyJson(httpLog.request_body), 'req')"
          >
            {{ copiedKey === "req" ? $t("common.copied") : $t("common.copy") }}
          </button>
        </div>
        <pre
          v-if="httpLog.request_body"
          class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
          >{{ prettyJson(httpLog.request_body) }}</pre
        >
        <div v-else class="rounded-lg border border-dashed border-border/30 p-3 text-xs">
          <p class="text-muted-foreground">{{ $t("settings.logs.notCaptured") }}</p>
          <p class="mt-1 text-muted-foreground/60">{{ $t("settings.logs.notCapturedHint") }}</p>
        </div>
      </div>

      <!-- Response Body -->
      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <h3 class="text-xs font-semibold tracking-wide text-foreground uppercase">
            {{ $t("settings.logs.responseBody") }}
          </h3>
          <button
            v-if="httpLog.response_body"
            class="text-[0.6875rem] text-muted-foreground hover:text-foreground"
            @click="copy(prettyJson(httpLog.response_body), 'res')"
          >
            {{ copiedKey === "res" ? $t("common.copied") : $t("common.copy") }}
          </button>
        </div>
        <pre
          v-if="httpLog.response_body"
          class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
          >{{ prettyJson(httpLog.response_body) }}</pre
        >
        <div v-else class="rounded-lg border border-dashed border-border/30 p-3 text-xs">
          <p class="text-muted-foreground">{{ $t("settings.logs.notCaptured") }}</p>
          <p class="mt-1 text-muted-foreground/60">{{ $t("settings.logs.notCapturedHint") }}</p>
        </div>
      </div>
    </div>

    <div v-else-if="llmLog" class="space-y-4">
      <!-- Meta -->
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
        <span class="font-mono text-foreground">{{ llmLog.provider }} / {{ llmLog.model }}</span>
        <span
          class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
          :class="
            llmLog.status === 'success'
              ? 'bg-emerald-500/10 text-emerald-500'
              : 'bg-red-500/10 text-red-500'
          "
        >
          {{ llmLog.status }}
        </span>
        <span
          >{{ llmLog.prompt_tokens }} in / {{ llmLog.completion_tokens }} out /
          {{ llmLog.total_tokens }} total</span
        >
        <span v-if="llmLog.estimated_cost_usd">${{ llmLog.estimated_cost_usd.toFixed(4) }}</span>
        <span>{{ llmLog.latency_ms.toFixed(0) }}ms</span>
        <span>{{ formatFullTimestamp(llmLog.created_at) }}</span>
      </div>
      <p v-if="llmLog.error_message" class="text-xs text-red-500">{{ llmLog.error_message }}</p>

      <!-- Request messages -->
      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <h3 class="text-xs font-semibold tracking-wide text-foreground uppercase">
            {{ $t("settings.logs.request") }}
          </h3>
          <button
            class="text-[0.6875rem] text-muted-foreground hover:text-foreground"
            @click="copy(prettyJson(llmLog.request_payload), 'req')"
          >
            {{ copiedKey === "req" ? $t("common.copied") : $t("common.copy") }}
          </button>
        </div>
        <div class="max-h-80 space-y-2 overflow-auto rounded-lg border border-border/20 p-2">
          <div v-for="(msg, i) in requestMessages" :key="i" class="rounded-lg bg-base-100/60 p-2.5">
            <span
              class="mb-1 inline-block rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
              :class="roleColors[msg.role] ?? 'bg-base-300 text-muted-foreground'"
            >
              {{ msg.role }}
            </span>
            <pre
              class="overflow-x-auto font-mono text-xs leading-relaxed whitespace-pre-wrap text-muted-foreground"
              >{{ msg.content }}</pre
            >
          </div>
        </div>
      </div>

      <!-- Response -->
      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <h3 class="text-xs font-semibold tracking-wide text-foreground uppercase">
            {{ $t("settings.logs.response") }}
          </h3>
          <button
            v-if="responsePayload"
            class="text-[0.6875rem] text-muted-foreground hover:text-foreground"
            @click="copy(prettyJson(responsePayload), 'res')"
          >
            {{ copiedKey === "res" ? $t("common.copied") : $t("common.copy") }}
          </button>
        </div>
        <div v-if="responsePayload" class="space-y-2">
          <pre
            v-if="responseContent"
            class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap text-foreground"
            >{{ responseContent }}</pre
          >
          <details v-if="responseReasoning" class="rounded-lg border border-border/20">
            <summary
              class="cursor-pointer px-3 py-2 text-xs font-medium text-muted-foreground select-none"
            >
              {{ $t("settings.logs.reasoning") }}
            </summary>
            <pre
              class="max-h-64 overflow-auto border-t border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap text-muted-foreground"
              >{{ responseReasoning }}</pre
            >
          </details>
          <pre
            v-if="responseMeta && Object.keys(responseMeta).length"
            class="overflow-x-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
            >{{ prettyJson(responseMeta) }}</pre
          >
        </div>
        <div v-else class="rounded-lg border border-dashed border-border/30 p-3 text-xs">
          <p class="text-muted-foreground">{{ $t("settings.logs.notCaptured") }}</p>
        </div>
      </div>
    </div>

    <div v-else-if="errLog" class="space-y-4">
      <!-- Meta -->
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span
          class="rounded-full bg-red-500/10 px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide text-red-500 uppercase"
        >
          {{ errLog.error_type }}
        </span>
        <span class="text-xs text-muted-foreground">{{
          formatFullTimestamp(errLog.created_at)
        }}</span>
      </div>
      <p class="text-sm text-foreground">{{ errLog.message }}</p>

      <div v-if="errLog.stack_trace">
        <h3 class="mb-1.5 text-xs font-semibold tracking-wide text-foreground uppercase">
          {{ $t("settings.logs.stackTrace") }}
        </h3>
        <pre
          class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
          >{{ errLog.stack_trace }}</pre
        >
      </div>

      <div v-if="Object.keys(errLog.context).length">
        <h3 class="mb-1.5 text-xs font-semibold tracking-wide text-foreground uppercase">
          {{ $t("settings.logs.context") }}
        </h3>
        <pre
          class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-base-100/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
          >{{ prettyJson(errLog.context) }}</pre
        >
      </div>
    </div>
  </Modal>
</template>
