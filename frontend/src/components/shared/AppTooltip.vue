<script setup lang="ts">
import { ref } from "vue";

// Lightweight tooltip: teleports the bubble to <body> so it escapes ancestor
// `overflow-hidden` (e.g. the collapsed sidebar). Positioned on hover/focus
// from the trigger's bounding rect. Replaces Nuxt UI's UTooltip.
const props = withDefaults(
  defineProps<{
    text?: string;
    side?: "top" | "right" | "bottom" | "left";
    disabled?: boolean;
    // Wrap long help text (max-width + normal whitespace) instead of the default
    // single-line label. Use for sentences, not short icon labels.
    wide?: boolean;
  }>(),
  { side: "top", disabled: false, wide: false },
);

const visible = ref(false);
const pos = ref<Record<string, string>>({});
const trigger = ref<HTMLElement | null>(null);
const OFFSET = 8;

function show() {
  if (props.disabled || !props.text || !trigger.value) return;
  const r = trigger.value.getBoundingClientRect();
  const cx = `${r.left + r.width / 2}px`;
  const cy = `${r.top + r.height / 2}px`;
  const map = {
    top: { left: cx, top: `${r.top - OFFSET}px`, transform: "translate(-50%, -100%)" },
    bottom: { left: cx, top: `${r.bottom + OFFSET}px`, transform: "translate(-50%, 0)" },
    right: { left: `${r.right + OFFSET}px`, top: cy, transform: "translate(0, -50%)" },
    left: { left: `${r.left - OFFSET}px`, top: cy, transform: "translate(-100%, -50%)" },
  } as const;
  pos.value = map[props.side];
  visible.value = true;
}

function hide() {
  visible.value = false;
}
</script>

<template>
  <span ref="trigger" @mouseenter="show" @mouseleave="hide" @focusin="show" @focusout="hide">
    <slot />
    <Teleport to="body">
      <span
        v-if="visible"
        role="tooltip"
        class="pointer-events-none fixed z-100 rounded-md bg-foreground px-2 py-1 text-xs font-medium text-base-100 shadow-md"
        :class="wide ? 'max-w-xs whitespace-normal wrap-break-word' : 'whitespace-nowrap'"
        :style="pos"
      >
        {{ text }}
      </span>
    </Teleport>
  </span>
</template>
