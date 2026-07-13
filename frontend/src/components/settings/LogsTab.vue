<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { client } from "@/api/client";
import type { components } from "@/api/schema";
import LogDetailModal from "@/components/settings/LogDetailModal.vue";

const { t } = useI18n();

// ── Types (generated from the backend OpenAPI spec) ────────
type HttpLog = components["schemas"]["HttpLogResponse"];
type LlmLog = components["schemas"]["LlmAuditLogResponse"];
type LlmStats = components["schemas"]["LlmStatsResponse"];
type UsageStat = components["schemas"]["LlmUsageStat"];
type ErrorLog = components["schemas"]["ErrorLogResponse"];

// ── State ──────────────────────────────────────────────────
const activeSubTab = ref<"http" | "llm" | "errors">("http");
const loading = ref(true);

const httpLogs = ref<HttpLog[]>([]);
const llmLogs = ref<LlmLog[]>([]);
const llmStats = ref<LlmStats | null>(null);
const errorLogs = ref<ErrorLog[]>([]);

type LogKind = "http" | "llm" | "error";
const selectedKind = ref<LogKind | null>(null);
const selectedLog = ref<HttpLog | LlmLog | ErrorLog | null>(null);

function openLog(kind: LogKind, log: HttpLog | LlmLog | ErrorLog) {
  selectedKind.value = kind;
  selectedLog.value = log;
}

function closeLog() {
  selectedKind.value = null;
  selectedLog.value = null;
}

// ── Formatting helpers ─────────────────────────────────────
function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

function formatDuration(ms: number): string {
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

function formatCost(usd: number | null | undefined): string {
  if (!usd) return "$0";
  return usd >= 1 ? `$${usd.toFixed(2)}` : `$${usd.toFixed(4)}`;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return t("time.justNow");
  if (diffMin < 60) return t("time.minutesAgo", { count: diffMin });
  if (diffHr < 24) return t("time.hoursAgo", { count: diffHr });
  if (diffDay < 7) return t("time.daysAgo", { count: diffDay });
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const methodColors: Record<string, string> = {
  GET: "bg-emerald-500/10 text-emerald-500",
  POST: "bg-blue-500/10 text-blue-500",
  PUT: "bg-amber-500/10 text-amber-500",
  DELETE: "bg-red-500/10 text-red-500",
};

const providerColors: Record<string, string> = {
  anthropic: "bg-orange-500/10 text-orange-500",
  openai: "bg-green-500/10 text-green-500",
  google: "bg-blue-500/10 text-blue-500",
  xai: "bg-purple-500/10 text-purple-500",
};

// ── Computed ───────────────────────────────────────────────
// The spec returns per provider+model rows; aggregate them for the summary cards.
const aggregate = computed(() => {
  const rows = llmStats.value?.stats ?? [];
  const sum = (pick: (r: UsageStat) => number | null | undefined) =>
    rows.reduce((acc, r) => acc + (pick(r) ?? 0), 0);
  const calls = sum((r) => r.total_calls);
  const weightedLatency = rows.reduce((acc, r) => acc + r.avg_latency_ms * r.total_calls, 0);
  return {
    requests: calls,
    success: sum((r) => r.success_count),
    tokens: sum((r) => r.total_tokens),
    cost: sum((r) => r.total_cost_usd),
    avgLatency: calls ? weightedLatency / calls : 0,
  };
});

const successRate = computed(() => {
  const { requests, success } = aggregate.value;
  return requests ? ((success / requests) * 100).toFixed(1) : "0";
});

const statCards = computed(() => {
  if (!llmStats.value) return [];
  const a = aggregate.value;
  return [
    {
      label: t("settings.logs.totalRequests"),
      value: String(a.requests),
      icon: "i-lucide-activity",
    },
    {
      label: t("settings.logs.totalTokens"),
      value: formatTokens(a.tokens),
      icon: "i-lucide-coins",
    },
    {
      label: t("settings.logs.successRate"),
      value: `${successRate.value}%`,
      icon: "i-lucide-check-circle",
    },
    {
      label: t("settings.logs.avgLatency"),
      value: formatDuration(a.avgLatency),
      icon: "i-lucide-timer",
    },
  ];
});

// Per provider+model usage rows, busiest first.
const usageRows = computed(() =>
  [...(llmStats.value?.stats ?? [])].sort((a, b) => b.total_calls - a.total_calls),
);

function rowSuccessRate(r: UsageStat): number {
  return r.total_calls ? Math.round((r.success_count / r.total_calls) * 100) : 0;
}

// ── Fetch ──────────────────────────────────────────────────
async function fetchAll() {
  loading.value = true;
  try {
    const [httpRes, llmRes, statsRes, errRes] = await Promise.all([
      client.GET("/admin/logs/http", { params: { query: { limit: 50 } } }),
      client.GET("/admin/logs/llm", { params: { query: { limit: 50 } } }),
      client.GET("/admin/logs/llm/stats"),
      client.GET("/admin/logs/errors", { params: { query: { limit: 50 } } }),
    ]);
    httpLogs.value = httpRes.data?.items ?? [];
    llmLogs.value = llmRes.data?.items ?? [];
    llmStats.value = statsRes.data ?? null;
    errorLogs.value = errRes.data?.items ?? [];
  } catch {
    // silently handle — backend/mocks may be unavailable
  } finally {
    loading.value = false;
  }
}

onMounted(fetchAll);
</script>

<template>
  <div class="mx-auto max-w-4xl animate-fade-in-up space-y-6">
    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <template v-else>
      <!-- LLM Usage Stats -->
      <section>
        <h3
          class="mb-3 font-cinzel text-sm font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ $t("settings.logs.llmUsage") }}
        </h3>

        <!-- Stat Cards -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div
            v-for="card in statCards"
            :key="card.label"
            class="rounded-xl border bg-base-200/50 p-4 text-center"
          >
            <AppIcon :name="card.icon" class="mx-auto mb-1 size-4 text-muted-foreground" />
            <p class="text-2xl font-bold text-foreground">{{ card.value }}</p>
            <p class="text-xs text-muted-foreground">{{ card.label }}</p>
          </div>
        </div>

        <!-- Per provider + model breakdown -->
        <div v-if="usageRows.length" class="mt-3 space-y-1.5">
          <span class="text-xs text-muted-foreground">{{ $t("settings.logs.byProvider") }}</span>
          <div
            v-for="row in usageRows"
            :key="`${row.provider}/${row.model}`"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/30 bg-base-300/10 px-3 py-2"
          >
            <span
              class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
              :class="providerColors[row.provider] ?? 'bg-base-300 text-muted-foreground'"
            >
              {{ row.provider }}
            </span>
            <span class="font-mono text-xs text-foreground">{{ row.model }}</span>
            <span class="flex-1" />
            <span class="text-xs text-muted-foreground">{{ row.total_calls }} calls</span>
            <span class="text-xs text-muted-foreground"
              >{{ formatTokens(row.total_tokens) }} tokens</span
            >
            <span class="text-xs text-muted-foreground">{{ formatCost(row.total_cost_usd) }}</span>
            <span class="text-xs text-muted-foreground">{{
              formatDuration(row.avg_latency_ms)
            }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide"
              :class="
                rowSuccessRate(row) >= 95
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-amber-500/10 text-amber-500'
              "
            >
              {{ rowSuccessRate(row) }}% ok
            </span>
          </div>
        </div>
      </section>

      <!-- Sub-tab selector -->
      <div class="flex items-center gap-2">
        <button
          v-for="tab in [
            { id: 'http' as const, label: $t('settings.logs.httpLogs'), icon: 'i-lucide-globe' },
            { id: 'llm' as const, label: $t('settings.logs.llmLogs'), icon: 'i-lucide-brain' },
            {
              id: 'errors' as const,
              label: $t('settings.logs.errorLogs'),
              icon: 'i-lucide-alert-triangle',
            },
          ]"
          :key="tab.id"
          class="relative rounded-full px-3.5 py-1.5 text-xs font-medium tracking-wide whitespace-nowrap transition-colors duration-200"
          :class="
            activeSubTab === tab.id
              ? 'bg-primary text-primary-content'
              : 'border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground'
          "
          @click="activeSubTab = tab.id"
        >
          <AppIcon :name="tab.icon" class="mr-1 inline-block size-3.5 align-text-bottom" />
          {{ tab.label }}
        </button>
      </div>

      <!-- HTTP Logs -->
      <section v-if="activeSubTab === 'http'" class="space-y-2">
        <div v-if="!httpLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t("settings.logs.noHttpLogs") }}
        </div>
        <button
          v-for="log in httpLogs"
          :key="log.id"
          type="button"
          class="flex w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/30 bg-base-300/10 px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-base-300/40"
          @click="openLog('http', log)"
        >
          <!-- Method -->
          <span
            class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
            :class="methodColors[log.method] ?? 'bg-base-300 text-muted-foreground'"
          >
            {{ log.method }}
          </span>

          <!-- Path -->
          <span class="font-mono text-sm text-foreground">{{ log.path }}</span>

          <!-- Status code -->
          <span
            class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide"
            :class="
              log.status_code < 300
                ? 'bg-emerald-500/10 text-emerald-500'
                : log.status_code < 400
                  ? 'bg-amber-500/10 text-amber-500'
                  : 'bg-red-500/10 text-red-500'
            "
          >
            {{ log.status_code }}
          </span>

          <!-- Spacer -->
          <span class="flex-1" />

          <!-- Latency -->
          <span class="text-xs text-muted-foreground">{{ formatDuration(log.latency_ms) }}</span>

          <!-- Request ID -->
          <span class="font-mono text-[0.625rem] text-muted-foreground/60">{{
            log.request_id
          }}</span>

          <!-- Timestamp -->
          <span class="text-xs text-muted-foreground">{{ formatTimestamp(log.created_at) }}</span>
        </button>
      </section>

      <!-- LLM Logs -->
      <section v-if="activeSubTab === 'llm'" class="space-y-2">
        <div v-if="!llmLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t("settings.logs.noLlmLogs") }}
        </div>
        <button
          v-for="log in llmLogs"
          :key="log.id"
          type="button"
          class="w-full rounded-lg border border-border/30 bg-base-300/10 px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-base-300/40"
          @click="openLog('llm', log)"
        >
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <!-- Provider -->
            <span
              class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
              :class="providerColors[log.provider] ?? 'bg-base-300 text-muted-foreground'"
            >
              {{ log.provider }}
            </span>

            <!-- Model -->
            <span class="font-mono text-sm text-foreground">{{ log.model }}</span>

            <!-- Status -->
            <span
              class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
              :class="
                log.status === 'success'
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-red-500/10 text-red-500'
              "
            >
              {{ log.status }}
            </span>

            <!-- Spacer -->
            <span class="flex-1" />

            <!-- Tokens -->
            <span class="text-xs text-muted-foreground">
              {{ formatTokens(log.prompt_tokens) }} in /
              {{ formatTokens(log.completion_tokens) }} out
            </span>

            <!-- Cost -->
            <span v-if="log.estimated_cost_usd" class="text-xs text-muted-foreground">
              {{ formatCost(log.estimated_cost_usd) }}
            </span>

            <!-- Latency -->
            <span class="text-xs text-muted-foreground">{{ formatDuration(log.latency_ms) }}</span>

            <!-- Timestamp -->
            <span class="text-xs text-muted-foreground">{{ formatTimestamp(log.created_at) }}</span>
          </div>

          <!-- Error message -->
          <p v-if="log.error_message" class="mt-1.5 text-xs text-red-500">
            {{ log.error_message }}
          </p>
        </button>
      </section>

      <!-- Error Logs -->
      <section v-if="activeSubTab === 'errors'" class="space-y-2">
        <div v-if="!errorLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t("settings.logs.noErrorLogs") }}
        </div>
        <button
          v-for="err in errorLogs"
          :key="err.id"
          type="button"
          class="flex w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/30 bg-base-300/10 px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-base-300/40"
          @click="openLog('error', err)"
        >
          <!-- Error type -->
          <span
            class="rounded-full bg-red-500/10 px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide text-red-500 uppercase"
          >
            {{ err.error_type }}
          </span>

          <!-- Message -->
          <span class="truncate text-sm text-foreground">{{ err.message }}</span>

          <!-- Spacer -->
          <span class="flex-1" />

          <!-- Timestamp -->
          <span class="text-xs text-muted-foreground">{{ formatTimestamp(err.created_at) }}</span>
        </button>
      </section>
    </template>

    <LogDetailModal
      :show="selectedKind !== null"
      :kind="selectedKind"
      :log="selectedLog"
      @close="closeLog"
    />
  </div>
</template>
