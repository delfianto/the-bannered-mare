<script setup lang="ts">
import { useCustomTheme, type CustomTheme } from "@/composables/useCustomTheme";

const { custom, set, reset } = useCustomTheme();

const fields: { key: keyof CustomTheme; label: string }[] = [
  { key: "primary", label: "Primary / accent" },
  { key: "base100", label: "Background" },
  { key: "base200", label: "Surface" },
  { key: "base300", label: "Muted / hover" },
  { key: "baseContent", label: "Text" },
];

function onColor(key: keyof CustomTheme, e: Event) {
  set(key, (e.target as HTMLInputElement).value);
}

function onHex(key: keyof CustomTheme, e: Event) {
  const v = (e.target as HTMLInputElement).value.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(v)) set(key, v.toLowerCase());
}
</script>

<template>
  <div class="animate-fade-in-up space-y-3 rounded-xl border bg-base-200/50 p-5">
    <div class="flex items-center justify-between">
      <h4 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">Custom theme</h4>
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
        @click="reset"
      >
        <AppIcon name="i-lucide-rotate-ccw" class="size-3" />
        Reset
      </button>
    </div>
    <p class="text-xs text-muted-foreground">
      Pick your colors — changes apply live, saved to this browser.
    </p>

    <div class="space-y-2.5">
      <div v-for="f in fields" :key="f.key" class="flex items-center justify-between gap-3">
        <span class="text-sm text-foreground">{{ f.label }}</span>
        <div class="flex items-center gap-2">
          <input
            type="text"
            :value="custom[f.key]"
            spellcheck="false"
            class="h-8 w-24 rounded-md border bg-base-100 px-2 font-mono text-xs text-foreground uppercase outline-none focus:border-primary/40"
            @change="onHex(f.key, $event)"
          />
          <input
            type="color"
            :value="custom[f.key]"
            :aria-label="f.label"
            class="size-8 shrink-0 cursor-pointer rounded-md border bg-transparent"
            @input="onColor(f.key, $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
