<script setup lang="ts">
defineProps<{
  label: string;
  hint?: string;
  charCount?: number;
  charMax?: number;
}>();
</script>

<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <label class="pl-0.5 text-sm font-medium text-foreground" style="letter-spacing: 0.01em">
        {{ label }}
      </label>
      <span v-if="hint" class="text-[11px] italic text-muted-foreground">{{ hint }}</span>
    </div>
    <slot />
    <div v-if="charMax !== undefined" class="flex justify-end">
      <span
        class="text-[11px]"
        :class="(charCount || 0) > charMax ? 'text-destructive' : 'text-muted-foreground'"
      >
        {{ charCount || 0 }}/{{ charMax }}
      </span>
    </div>
  </div>
</template>
