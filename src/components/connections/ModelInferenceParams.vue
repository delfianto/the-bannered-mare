<script setup lang="ts">
import { computed } from "vue";
import ParamInput from "./ParamInput.vue";

const props = defineProps<{
  familyParameters: Record<string, any>;
  modelParameters: Record<string, unknown>;
  parameterDocs: Record<string, { label: string; short_info: string; detailed_info: string }>;
}>();

const emit = defineEmits<{
  "update:modelParameters": [value: Record<string, unknown>];
}>();

type ParamGroup = "general" | "fine-tuning" | "advanced";

function categorizeParam(_key: string, schema: any): ParamGroup {
  const type = schema?.type;
  if (type === "object" || type === "list" || type === "json" || type === "string") {
    return "advanced";
  }
  if ((type === "int" || type === "float") && schema?.min_value !== undefined && schema?.max_value !== undefined) {
    return "fine-tuning";
  }
  return "general";
}

const groupedParams = computed(() => {
  const groups: Record<ParamGroup, string[]> = {
    general: [],
    "fine-tuning": [],
    advanced: [],
  };
  if (!props.familyParameters) return groups;
  for (const key of Object.keys(props.familyParameters)) {
    const category = categorizeParam(key, props.familyParameters[key]);
    groups[category].push(key);
  }
  return groups;
});

const overrideCount = computed(() => {
  return Object.keys(props.modelParameters || {}).length;
});

function overrideCountForGroup(keys: string[]): number {
  return keys.filter((k) => props.modelParameters?.[k] !== undefined).length;
}

function isOverridden(key: string): boolean {
  return props.modelParameters?.[key] !== undefined;
}

function getLabel(key: string): string {
  return props.parameterDocs?.[key]?.label || humanize(key);
}

function getTooltip(key: string): string {
  return props.parameterDocs?.[key]?.short_info || "";
}

function humanize(str: string): string {
  return str
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getValue(key: string): unknown {
  if (props.modelParameters?.[key] !== undefined) {
    return props.modelParameters[key];
  }
  return props.familyParameters?.[key]?.default;
}

function updateParam(key: string, value: unknown) {
  emit("update:modelParameters", {
    ...props.modelParameters,
    [key]: value,
  });
}

function resetToDefaults() {
  emit("update:modelParameters", {});
}

const sections = computed(() => {
  const result: { key: ParamGroup; label: string; icon: string; params: string[] }[] = [];
  if (groupedParams.value.general.length) {
    result.push({
      key: "general",
      label: "General",
      icon: "i-lucide-settings-2",
      params: groupedParams.value.general,
    });
  }
  if (groupedParams.value["fine-tuning"].length) {
    result.push({
      key: "fine-tuning",
      label: "Fine-Tuning",
      icon: "i-lucide-sliders-horizontal",
      params: groupedParams.value["fine-tuning"],
    });
  }
  if (groupedParams.value.advanced.length) {
    result.push({
      key: "advanced",
      label: "Advanced",
      icon: "i-lucide-box",
      params: groupedParams.value.advanced,
    });
  }
  return result;
});
</script>

<template>
  <div class="space-y-5">
    <!-- Reset button -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span v-if="overrideCount > 0" class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/15 px-1.5 text-[10px] font-semibold text-primary">
          {{ overrideCount }}
        </span>
        <span>{{ overrideCount > 0 ? "parameter overrides" : "Using family defaults" }}</span>
      </div>
      <button
        v-if="overrideCount > 0"
        class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        @click="resetToDefaults"
      >
        <UIcon name="i-lucide-rotate-ccw" class="h-3 w-3" />
        Reset to Defaults
      </button>
    </div>

    <!-- Sections -->
    <div v-for="section in sections" :key="section.key" class="space-y-3">
      <!-- Section header -->
      <div class="flex items-center gap-2">
        <UIcon :name="section.icon" class="h-4 w-4 text-muted-foreground" />
        <h3 class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          {{ section.label }}
        </h3>
        <span
          v-if="overrideCountForGroup(section.params) > 0"
          class="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[9px] font-semibold text-primary"
        >
          {{ overrideCountForGroup(section.params) }}
        </span>
      </div>

      <!-- General: compact grid -->
      <div
        v-if="section.key === 'general'"
        class="space-y-2"
      >
        <div
          v-for="paramKey in section.params"
          :key="paramKey"
          class="flex items-center justify-between gap-3 rounded-lg border border-border/30 bg-muted/10 px-3 py-2"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span
              v-if="isOverridden(paramKey)"
              class="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
            />
            <span class="truncate text-sm text-foreground">{{ getLabel(paramKey) }}</span>
            <UTooltip v-if="getTooltip(paramKey)" :text="getTooltip(paramKey)">
              <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0 cursor-help text-muted-foreground/50" />
            </UTooltip>
          </div>
          <ParamInput
            :param-key="paramKey"
            :schema="familyParameters[paramKey]"
            :model-value="getValue(paramKey)"
            layout="horizontal"
            @update:model-value="(val: unknown) => updateParam(paramKey, val)"
          />
        </div>
      </div>

      <!-- Fine-Tuning: sliders (2-col grid) -->
      <div
        v-else-if="section.key === 'fine-tuning'"
        class="grid grid-cols-1 gap-3 lg:grid-cols-2"
      >
        <div
          v-for="paramKey in section.params"
          :key="paramKey"
          class="rounded-lg border border-border/30 bg-muted/10 px-3 py-2.5"
        >
          <div class="mb-2 flex items-center gap-2">
            <span
              v-if="isOverridden(paramKey)"
              class="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
            />
            <span class="text-sm text-foreground">{{ getLabel(paramKey) }}</span>
            <UTooltip v-if="getTooltip(paramKey)" :text="getTooltip(paramKey)">
              <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0 cursor-help text-muted-foreground/50" />
            </UTooltip>
          </div>
          <ParamInput
            :param-key="paramKey"
            :schema="familyParameters[paramKey]"
            :model-value="getValue(paramKey)"
            layout="horizontal"
            @update:model-value="(val: unknown) => updateParam(paramKey, val)"
          />
        </div>
      </div>

      <!-- Advanced: full-width vertical -->
      <div
        v-else
        class="space-y-3"
      >
        <div
          v-for="paramKey in section.params"
          :key="paramKey"
          class="rounded-lg border border-border/30 bg-muted/10 px-3 py-2.5"
        >
          <div class="mb-2 flex items-center gap-2">
            <span
              v-if="isOverridden(paramKey)"
              class="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
            />
            <span class="text-sm text-foreground">{{ getLabel(paramKey) }}</span>
            <UTooltip v-if="getTooltip(paramKey)" :text="getTooltip(paramKey)">
              <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0 cursor-help text-muted-foreground/50" />
            </UTooltip>
          </div>
          <ParamInput
            :param-key="paramKey"
            :schema="familyParameters[paramKey]"
            :model-value="getValue(paramKey)"
            layout="vertical"
            @update:model-value="(val: unknown) => updateParam(paramKey, val)"
          />
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!sections.length" class="py-6 text-center text-sm text-muted-foreground">
      No parameters defined for this model family.
    </div>
  </div>
</template>
