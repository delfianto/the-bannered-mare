<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

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
const expandedErrors = ref<Set<string>>(new Set());

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

  if (diffMin < 1) return t('time.justNow');
  if (diffMin < 60) return t('time.minutesAgo', { count: diffMin });
  if (diffHr < 24) return t('time.hoursAgo', { count: diffHr });
  if (diffDay < 7) return t('time.daysAgo', { count: diffDay });
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
    { label: t('settings.logs.totalRequests'), value: String(a.requests), icon: "i-lucide-activity" },
    { label: t('settings.logs.totalTokens'), value: formatTokens(a.tokens), icon: "i-lucide-coins" },
    { label: t('settings.logs.successRate'), value: `${successRate.value}%`, icon: "i-lucide-check-circle" },
    { label: t('settings.logs.avgLatency'), value: formatDuration(a.avgLatency), icon: "i-lucide-timer" },
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
    httpLogs.value = httpRes.data?.logs ?? [];
    llmLogs.value = llmRes.data?.logs ?? [];
    llmStats.value = statsRes.data ?? null;
    errorLogs.value = errRes.data?.logs ?? [];
  } catch {
    // silently handle — backend/mocks may be unavailable
  } finally {
    loading.value = false;
  }
}

function toggleError(id: string) {
  if (expandedErrors.value.has(id)) {
    expandedErrors.value.delete(id);
  } else {
    expandedErrors.value.add(id);
  }
}

onMounted(fetchAll);
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6 animate-fade-in-up">
    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-muted-foreground" />
    </div>

    <template v-else>
      <!-- LLM Usage Stats -->
      <section>
        <h3
          class="mb-3 font-cinzel text-sm font-semibold uppercase tracking-widest text-muted-foreground"
        >
          {{ $t('settings.logs.llmUsage') }}
        </h3>

        <!-- Stat Cards -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div
            v-for="card in statCards"
            :key="card.label"
            class="rounded-xl border bg-card/50 p-4 text-center"
          >
            <UIcon :name="card.icon" class="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
            <p class="text-2xl font-bold text-foreground">{{ card.value }}</p>
            <p class="text-xs text-muted-foreground">{{ card.label }}</p>
          </div>
        </div>

        <!-- Per provider + model breakdown -->
        <div v-if="usageRows.length" class="mt-3 space-y-1.5">
          <span class="text-xs text-muted-foreground">{{ $t('settings.logs.byProvider') }}</span>
          <div
            v-for="row in usageRows"
            :key="`${row.provider}/${row.model}`"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/30 bg-muted/10 px-3 py-2"
          >
            <span
              class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
              :class="providerColors[row.provider] ?? 'bg-muted text-muted-foreground'"
            >
              {{ row.provider }}
            </span>
            <span class="font-mono text-xs text-foreground">{{ row.model }}</span>
            <span class="flex-1" />
            <span class="text-xs text-muted-foreground">{{ row.total_calls }} calls</span>
            <span class="text-xs text-muted-foreground">{{ formatTokens(row.total_tokens) }} tokens</span>
            <span class="text-xs text-muted-foreground">{{ formatCost(row.total_cost_usd) }}</span>
            <span class="text-xs text-muted-foreground">{{ formatDuration(row.avg_latency_ms) }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-[9px] font-medium tracking-wide"
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
            { id: 'errors' as const, label: $t('settings.logs.errorLogs'), icon: 'i-lucide-alert-triangle' },
          ]"
          :key="tab.id"
          class="relative whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium tracking-wide transition-colors duration-200"
          :class="
            activeSubTab === tab.id
              ? 'bg-primary text-primary-foreground'
              : 'border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground'
          "
          @click="activeSubTab = tab.id"
        >
          <UIcon :name="tab.icon" class="mr-1 inline-block h-3.5 w-3.5 align-text-bottom" />
          {{ tab.label }}
        </button>
      </div>

      <!-- HTTP Logs -->
      <section v-if="activeSubTab === 'http'" class="space-y-2">
        <div v-if="!httpLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t('settings.logs.noHttpLogs') }}
        </div>
        <div
          v-for="log in httpLogs"
          :key="log.id"
          class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-border/30 bg-muted/10 px-4 py-3"
        >
          <!-- Method -->
          <span
            class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
            :class="methodColors[log.method] ?? 'bg-muted text-muted-foreground'"
          >
            {{ log.method }}
          </span>

          <!-- Path -->
          <span class="font-mono text-sm text-foreground">{{ log.path }}</span>

          <!-- Status code -->
          <span
            class="rounded-full px-2 py-0.5 text-[9px] font-medium tracking-wide"
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
          <span class="font-mono text-[10px] text-muted-foreground/60">{{ log.request_id }}</span>

          <!-- Timestamp -->
          <span class="text-xs text-muted-foreground">{{ formatTimestamp(log.created_at) }}</span>
        </div>
      </section>

      <!-- LLM Logs -->
      <section v-if="activeSubTab === 'llm'" class="space-y-2">
        <div v-if="!llmLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t('settings.logs.noLlmLogs') }}
        </div>
        <div
          v-for="log in llmLogs"
          :key="log.id"
          class="rounded-lg border border-border/30 bg-muted/10 px-4 py-3"
        >
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <!-- Provider -->
            <span
              class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
              :class="providerColors[log.provider] ?? 'bg-muted text-muted-foreground'"
            >
              {{ log.provider }}
            </span>

            <!-- Model -->
            <span class="font-mono text-sm text-foreground">{{ log.model }}</span>

            <!-- Status -->
            <span
              class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
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
              {{ formatTokens(log.prompt_tokens) }} in / {{ formatTokens(log.completion_tokens) }} out
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
        </div>
      </section>

      <!-- Error Logs -->
      <section v-if="activeSubTab === 'errors'" class="space-y-2">
        <div v-if="!errorLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          {{ $t('settings.logs.noErrorLogs') }}
        </div>
        <div
          v-for="err in errorLogs"
          :key="err.id"
          class="rounded-lg border border-border/30 bg-muted/10 px-4 py-3"
        >
          <button
            class="flex w-full flex-wrap items-center gap-x-3 gap-y-1 text-left"
            @click="toggleError(err.id)"
          >
            <!-- Error type -->
            <span
              class="rounded-full bg-red-500/10 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-red-500"
            >
              {{ err.error_type }}
            </span>

            <!-- Message -->
            <span class="text-sm text-foreground">{{ err.message }}</span>

            <!-- Spacer -->
            <span class="flex-1" />

            <!-- Timestamp -->
            <span class="text-xs text-muted-foreground">{{ formatTimestamp(err.created_at) }}</span>

            <!-- Expand indicator -->
            <UIcon
              name="i-lucide-chevron-down"
              class="h-3.5 w-3.5 text-muted-foreground transition-transform duration-200"
              :class="expandedErrors.has(err.id) ? 'rotate-180' : ''"
            />
          </button>

          <!-- Stack trace + context (expandable) -->
          <div v-if="expandedErrors.has(err.id)" class="mt-3 space-y-2">
            <pre
              v-if="err.stack_trace"
              class="overflow-x-auto rounded-lg border border-border/20 bg-background/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
            >{{ err.stack_trace }}</pre>
            <pre
              v-if="Object.keys(err.context).length"
              class="overflow-x-auto rounded-lg border border-border/20 bg-background/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
            >{{ JSON.stringify(err.context, null, 2) }}</pre>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
