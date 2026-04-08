<script setup lang="ts">
import { ref, onMounted, computed } from "vue";

// ── Types ──────────────────────────────────────────────────
interface HttpLog {
  id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  timestamp: string;
  request_id: string;
}

interface LlmLog {
  id: string;
  provider: string;
  model: string;
  chat_id: string;
  status: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  duration_ms: number;
  timestamp: string;
  error?: string;
}

interface LlmStats {
  total_requests: number;
  successful: number;
  failed: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  avg_duration_ms: number;
  by_provider: Record<string, { requests: number; tokens: number }>;
}

interface ErrorLog {
  id: string;
  error_type: string;
  message: string;
  path: string;
  timestamp: string;
  stack_trace: string;
}

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
  return `${ms}ms`;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
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
const successRate = computed(() => {
  if (!llmStats.value) return "0";
  return ((llmStats.value.successful / llmStats.value.total_requests) * 100).toFixed(1);
});

const statCards = computed(() => {
  if (!llmStats.value) return [];
  return [
    { label: "Total Requests", value: String(llmStats.value.total_requests), icon: "i-lucide-activity" },
    { label: "Total Tokens", value: formatTokens(llmStats.value.total_tokens), icon: "i-lucide-coins" },
    { label: "Success Rate", value: `${successRate.value}%`, icon: "i-lucide-check-circle" },
    { label: "Avg Latency", value: formatDuration(llmStats.value.avg_duration_ms), icon: "i-lucide-timer" },
  ];
});

const providerEntries = computed(() => {
  if (!llmStats.value) return [];
  return Object.entries(llmStats.value.by_provider).map(([name, data]) => ({
    name,
    requests: data.requests,
    tokens: formatTokens(data.tokens),
  }));
});

// ── Fetch ──────────────────────────────────────────────────
async function fetchAll() {
  loading.value = true;
  try {
    const [httpRes, llmRes, statsRes, errRes] = await Promise.all([
      fetch("/admin/logs/http?limit=50"),
      fetch("/admin/logs/llm?limit=50"),
      fetch("/admin/logs/llm/stats"),
      fetch("/admin/logs/errors?limit=50"),
    ]);
    httpLogs.value = await httpRes.json();
    llmLogs.value = await llmRes.json();
    llmStats.value = await statsRes.json();
    errorLogs.value = await errRes.json();
  } catch {
    // silently handle — MSW may not be ready
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
          LLM Usage
        </h3>

        <!-- Stat Cards -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div
            v-for="card in statCards"
            :key="card.label"
            class="rounded-xl border border-border bg-card/50 p-4 text-center"
          >
            <UIcon :name="card.icon" class="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
            <p class="text-2xl font-bold text-foreground">{{ card.value }}</p>
            <p class="text-xs text-muted-foreground">{{ card.label }}</p>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div v-if="providerEntries.length" class="mt-3 flex flex-wrap items-center gap-2">
          <span class="text-xs text-muted-foreground">By provider:</span>
          <span
            v-for="prov in providerEntries"
            :key="prov.name"
            class="rounded-full px-2.5 py-0.5 text-[10px] font-medium capitalize tracking-wide"
            :class="providerColors[prov.name] ?? 'bg-muted text-muted-foreground'"
          >
            {{ prov.name }} &middot; {{ prov.requests }} req &middot; {{ prov.tokens }} tokens
          </span>
        </div>
      </section>

      <!-- Sub-tab selector -->
      <div class="flex items-center gap-2">
        <button
          v-for="tab in [
            { id: 'http' as const, label: 'HTTP Logs', icon: 'i-lucide-globe' },
            { id: 'llm' as const, label: 'LLM Logs', icon: 'i-lucide-brain' },
            { id: 'errors' as const, label: 'Error Logs', icon: 'i-lucide-alert-triangle' },
          ]"
          :key="tab.id"
          class="relative whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium tracking-wide transition-colors duration-200"
          :class="
            activeSubTab === tab.id
              ? 'bg-primary text-primary-foreground'
              : 'border border-border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground'
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
          No HTTP logs found.
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

          <!-- Duration -->
          <span class="text-xs text-muted-foreground">{{ formatDuration(log.duration_ms) }}</span>

          <!-- Request ID -->
          <span class="font-mono text-[10px] text-muted-foreground/60">{{ log.request_id }}</span>

          <!-- Timestamp -->
          <span class="text-xs text-muted-foreground">{{ formatTimestamp(log.timestamp) }}</span>
        </div>
      </section>

      <!-- LLM Logs -->
      <section v-if="activeSubTab === 'llm'" class="space-y-2">
        <div v-if="!llmLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          No LLM logs found.
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
              {{ formatTokens(log.input_tokens) }} in / {{ formatTokens(log.output_tokens) }} out
            </span>

            <!-- Duration -->
            <span class="text-xs text-muted-foreground">{{ formatDuration(log.duration_ms) }}</span>

            <!-- Timestamp -->
            <span class="text-xs text-muted-foreground">{{ formatTimestamp(log.timestamp) }}</span>
          </div>

          <!-- Error message -->
          <p v-if="log.error" class="mt-1.5 text-xs text-red-500">
            {{ log.error }}
          </p>
        </div>
      </section>

      <!-- Error Logs -->
      <section v-if="activeSubTab === 'errors'" class="space-y-2">
        <div v-if="!errorLogs.length" class="py-8 text-center text-sm text-muted-foreground">
          No error logs found.
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

            <!-- Path -->
            <span class="font-mono text-xs text-muted-foreground">{{ err.path }}</span>

            <!-- Timestamp -->
            <span class="text-xs text-muted-foreground">{{ formatTimestamp(err.timestamp) }}</span>

            <!-- Expand indicator -->
            <UIcon
              name="i-lucide-chevron-down"
              class="h-3.5 w-3.5 text-muted-foreground transition-transform duration-200"
              :class="expandedErrors.has(err.id) ? 'rotate-180' : ''"
            />
          </button>

          <!-- Stack trace (expandable) -->
          <pre
            v-if="expandedErrors.has(err.id)"
            class="mt-3 overflow-x-auto rounded-lg border border-border/20 bg-background/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground"
          >{{ err.stack_trace }}</pre>
        </div>
      </section>
    </template>
  </div>
</template>
