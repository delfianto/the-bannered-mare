<script setup lang="ts">
// DaisyUI-styled switch. Supports v-model (boolean) and a `change` event for
// call sites that run a handler (e.g. async enable/disable). Replaces the
// hand-rolled role="switch" toggle divs.
withDefaults(
  defineProps<{
    modelValue?: boolean;
    disabled?: boolean;
    ariaLabel?: string;
  }>(),
  { modelValue: false, disabled: false },
);

const emit = defineEmits<{ "update:modelValue": [value: boolean]; change: [value: boolean] }>();

function onChange(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  emit("update:modelValue", checked);
  emit("change", checked);
}
</script>

<template>
  <input
    type="checkbox"
    role="switch"
    class="toggle toggle-primary"
    :checked="modelValue"
    :disabled="disabled"
    :aria-label="ariaLabel"
    @change="onChange"
  />
</template>
