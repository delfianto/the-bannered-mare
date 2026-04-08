<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  paramKey: string;
  schema: any;
  modelValue: unknown;
  layout?: "horizontal" | "vertical";
}>();

const emit = defineEmits<{
  "update:modelValue": [value: unknown];
}>();

const layout = computed(() => props.layout || "horizontal");

const currentValue = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const schemaType = computed(() => props.schema?.type || "string");

const isEnabledDisabledEnum = computed(
  () =>
    schemaType.value === "enum" &&
    props.schema?.str_values?.length === 2 &&
    props.schema.str_values.includes("enabled") &&
    props.schema.str_values.includes("disabled"),
);

const hasRange = computed(
  () => props.schema?.min_value !== undefined && props.schema?.max_value !== undefined,
);

const step = computed(() => (schemaType.value === "float" ? 0.01 : 1));

const numberValue = computed({
  get: () => {
    const v = currentValue.value;
    return typeof v === "number" ? v : (props.schema?.default ?? 0);
  },
  set: (val) => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (!isNaN(num)) {
      currentValue.value = schemaType.value === "int" ? Math.round(num) : num;
    }
  },
});

const boolValue = computed({
  get: () => !!currentValue.value,
  set: (val) => {
    currentValue.value = val;
  },
});

const enabledDisabledValue = computed({
  get: () => currentValue.value === "enabled",
  set: (val) => {
    currentValue.value = val ? "enabled" : "disabled";
  },
});

const stringValue = computed({
  get: () => (typeof currentValue.value === "string" ? currentValue.value : ""),
  set: (val) => {
    currentValue.value = val;
  },
});

const selectValue = computed({
  get: () => (currentValue.value != null ? String(currentValue.value) : (props.schema?.default != null ? String(props.schema.default) : "")),
  set: (val) => {
    currentValue.value = val;
  },
});

const jsonValue = computed({
  get: () => {
    try {
      return currentValue.value != null ? JSON.stringify(currentValue.value, null, 2) : "";
    } catch {
      return String(currentValue.value ?? "");
    }
  },
  set: (val) => {
    try {
      currentValue.value = JSON.parse(val);
    } catch {
      // Keep as string if not valid JSON
    }
  },
});

// Tag input for list of strings
const tagItems = computed({
  get: () => (Array.isArray(currentValue.value) ? (currentValue.value as string[]) : []),
  set: (val) => {
    currentValue.value = val;
  },
});

function addTag(value: string) {
  const trimmed = value.trim();
  if (trimmed && !tagItems.value.includes(trimmed)) {
    tagItems.value = [...tagItems.value, trimmed];
  }
}

function removeTag(index: number) {
  const copy = [...tagItems.value];
  copy.splice(index, 1);
  tagItems.value = copy;
}

function handleTagKeydown(event: KeyboardEvent) {
  if (event.key === "Enter") {
    event.preventDefault();
    const target = event.target as HTMLInputElement;
    addTag(target.value);
    target.value = "";
  }
}

// List of objects
const listItems = computed({
  get: () => (Array.isArray(currentValue.value) ? (currentValue.value as any[]) : []),
  set: (val) => {
    currentValue.value = val;
  },
});

function updateListItem(index: number, val: any) {
  const copy = [...listItems.value];
  copy[index] = val;
  listItems.value = copy;
}

// Object properties
const objectValue = computed({
  get: () => {
    if (typeof currentValue.value === "object" && currentValue.value !== null) {
      return currentValue.value as Record<string, unknown>;
    }
    return {};
  },
  set: (val) => {
    currentValue.value = val;
  },
});

function updateObjectProp(key: string, val: unknown) {
  objectValue.value = { ...objectValue.value, [key]: val };
}
</script>

<template>
  <!-- Boolean toggle -->
  <template v-if="schemaType === 'boolean'">
    <button @click="boolValue = !boolValue" class="cursor-pointer">
      <div
        class="flex h-[22px] w-10 items-center rounded-full px-[3px]"
        :class="boolValue ? 'bg-primary' : 'bg-muted-foreground/40'"
      >
        <span
          class="h-4 w-4 rounded-full shadow-sm transition-transform"
          :class="boolValue ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
        />
      </div>
    </button>
  </template>

  <!-- Enabled/Disabled enum as toggle -->
  <template v-else-if="isEnabledDisabledEnum">
    <button @click="enabledDisabledValue = !enabledDisabledValue" class="cursor-pointer">
      <div
        class="flex h-[22px] w-10 items-center rounded-full px-[3px]"
        :class="enabledDisabledValue ? 'bg-primary' : 'bg-muted-foreground/40'"
      >
        <span
          class="h-4 w-4 rounded-full shadow-sm transition-transform"
          :class="enabledDisabledValue ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
        />
      </div>
    </button>
  </template>

  <!-- Enum select -->
  <template v-else-if="schemaType === 'enum'">
    <USelectMenu
      v-model="selectValue"
      :items="(schema.str_values || []).map((v: string) => ({ label: v, value: v }))"
      value-key="value"
      :search-input="false"
      :class="layout === 'horizontal' ? 'max-w-[180px]' : 'w-full'"
      :ui="{
        base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
        content: 'border border-border bg-card ring-0 outline-none shadow-lg',
        item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
      }"
    >
      <button
        class="flex h-9 items-center justify-between gap-2 rounded-lg border border-border bg-muted/40 px-3 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30"
        :class="layout === 'horizontal' ? 'w-[180px]' : 'w-full'"
      >
        <span class="truncate">{{ selectValue || 'Select...' }}</span>
        <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      </button>
    </USelectMenu>
  </template>

  <!-- Number with range slider -->
  <template v-else-if="(schemaType === 'int' || schemaType === 'float') && hasRange">
    <div class="flex items-center gap-3" :class="layout === 'horizontal' ? 'max-w-[280px]' : 'w-full'">
      <input
        type="range"
        :min="schema.min_value"
        :max="schema.max_value"
        :step="step"
        :value="numberValue"
        class="param-slider h-2 w-full cursor-pointer"
        @input="numberValue = parseFloat(($event.target as HTMLInputElement).value)"
      />
      <input
        type="number"
        :min="schema.min_value"
        :max="schema.max_value"
        :step="step"
        :value="numberValue"
        class="h-9 w-[90px] shrink-0 rounded-lg border border-border bg-muted/40 px-3 text-center font-mono text-sm text-foreground outline-none transition-all focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="numberValue = parseFloat(($event.target as HTMLInputElement).value)"
      />
    </div>
  </template>

  <!-- Number without range -->
  <template v-else-if="schemaType === 'int' || schemaType === 'float'">
    <input
      type="number"
      :step="step"
      :min="schema.min_value"
      :max="schema.max_value"
      :value="numberValue"
      class="h-9 rounded-lg border border-border bg-muted/40 px-3 font-mono text-sm text-foreground outline-none transition-all focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
      :class="layout === 'horizontal' ? 'w-[120px]' : 'w-full'"
      @input="numberValue = parseFloat(($event.target as HTMLInputElement).value)"
    />
  </template>

  <!-- String -->
  <template v-else-if="schemaType === 'string'">
    <textarea
      v-if="layout === 'vertical'"
      v-model="stringValue"
      rows="3"
      class="w-full rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
    />
    <input
      v-else
      v-model="stringValue"
      type="text"
      class="h-9 max-w-[280px] rounded-lg border border-border bg-muted/40 px-3 text-sm text-foreground outline-none transition-all focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
    />
  </template>

  <!-- List of strings (tag input) -->
  <template v-else-if="schemaType === 'list' && schema.item_schema?.type === 'string'">
    <div class="w-full space-y-2">
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="(tag, i) in tagItems"
          :key="i"
          class="inline-flex items-center gap-1 rounded-full bg-accent px-2.5 py-0.5 text-xs text-foreground"
        >
          {{ tag }}
          <button
            class="ml-0.5 text-muted-foreground hover:text-foreground"
            @click="removeTag(i)"
          >
            <UIcon name="i-lucide-x" class="h-3 w-3" />
          </button>
        </span>
      </div>
      <input
        type="text"
        placeholder="Type and press Enter"
        class="h-9 w-full rounded-lg border border-border bg-muted/40 px-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @keydown="handleTagKeydown"
      />
    </div>
  </template>

  <!-- List of objects -->
  <template v-else-if="schemaType === 'list' && schema.item_schema?.type === 'object'">
    <div class="w-full space-y-3">
      <div
        v-for="(item, i) in listItems"
        :key="i"
        class="rounded-lg border border-border/50 bg-muted/10 p-3"
      >
        <div class="mb-1 text-[10px] font-medium uppercase text-muted-foreground">
          Item {{ i + 1 }}
        </div>
        <div class="space-y-2">
          <div
            v-for="(propSchema, propKey) in schema.item_schema.properties"
            :key="propKey"
            class="flex items-center justify-between gap-3"
          >
            <span class="shrink-0 font-mono text-xs text-muted-foreground">{{ propKey }}</span>
            <ParamInput
              :param-key="String(propKey)"
              :schema="propSchema"
              :model-value="item?.[propKey]"
              layout="horizontal"
              @update:model-value="(val: unknown) => updateListItem(i, { ...item, [propKey]: val })"
            />
          </div>
        </div>
      </div>
    </div>
  </template>

  <!-- Object with properties -->
  <template v-else-if="schemaType === 'object' && schema.properties">
    <div class="w-full space-y-2">
      <div
        v-for="(propSchema, propKey) in schema.properties"
        :key="propKey"
        class="flex items-center justify-between gap-3"
      >
        <span class="shrink-0 font-mono text-xs text-muted-foreground">{{ propKey }}</span>
        <ParamInput
          :param-key="String(propKey)"
          :schema="propSchema"
          :model-value="objectValue[String(propKey)]"
          layout="horizontal"
          @update:model-value="(val: unknown) => updateObjectProp(String(propKey), val)"
        />
      </div>
    </div>
  </template>

  <!-- JSON -->
  <template v-else-if="schemaType === 'json'">
    <textarea
      v-model="jsonValue"
      rows="4"
      class="w-full rounded-lg border border-border bg-muted/40 px-4 py-3 font-mono text-xs text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
      :class="layout === 'horizontal' ? 'max-w-[300px]' : ''"
    />
  </template>

  <!-- Fallback -->
  <template v-else>
    <span class="text-xs text-muted-foreground">Unsupported type: {{ schemaType }}</span>
  </template>
</template>

<style scoped>
.param-slider {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  border-radius: 9999px;
}

/* Track */
.param-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--border);
}

.param-slider::-moz-range-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--border);
}

/* Thumb */
.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  margin-top: -5px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.param-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  border: none;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.param-slider:focus {
  outline: none;
}
</style>
