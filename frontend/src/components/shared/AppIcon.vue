<script setup lang="ts">
import { computed, type Component } from "vue";
import { icons, fallbackIcon } from "./icons";

// Accepts bare kebab names ("home") and the legacy "i-lucide-home" / "lucide:home"
// forms, so call sites and the icon strings in constants/ need no changes.
const props = defineProps<{ name?: string }>();

const resolved = computed<Component>(() => {
  const key = (props.name ?? "").replace(/^i-lucide-/, "").replace(/^lucide:/, "");
  const icon = icons[key];
  if (!icon && props.name && import.meta.env.DEV) {
    console.warn(`[AppIcon] unknown icon "${props.name}"`);
  }
  return icon ?? fallbackIcon;
});
</script>

<template>
  <component :is="resolved" />
</template>
