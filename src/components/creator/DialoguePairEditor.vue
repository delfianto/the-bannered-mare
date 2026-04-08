<script setup lang="ts">
import type { DialoguePair } from "@/types/creator";

defineProps<{
  pair: DialoguePair;
  index: number;
}>();

const emit = defineEmits<{
  update: [id: string, field: "userMessage" | "characterReply", value: string];
  remove: [id: string];
}>();
</script>

<template>
  <div class="relative space-y-3 rounded-xl border bg-muted/20 p-4">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-muted-foreground">Exchange #{{ index + 1 }}</span>
      <button
        type="button"
        class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
        @click="emit('remove', pair.id)"
      >
        <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
      </button>
    </div>

    <div class="space-y-1.5">
      <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <UIcon name="i-lucide-user" class="h-3 w-3" />
        <span>User</span>
      </div>
      <textarea
        :value="pair.userMessage"
        placeholder='*Examines the runes.* "What do they say?"'
        rows="2"
        class="w-full resize-y rounded-lg border bg-background px-3 py-2.5 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update', pair.id, 'userMessage', ($event.target as HTMLTextAreaElement).value)"
      />
    </div>

    <div class="space-y-1.5">
      <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <UIcon name="i-lucide-bot" class="h-3 w-3" />
        <span>Character</span>
      </div>
      <textarea
        :value="pair.characterReply"
        placeholder='*Traces the inscription.* "The script speaks of a key — not of metal, but of intent."'
        rows="3"
        class="w-full resize-y rounded-lg border bg-background px-3 py-2.5 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update', pair.id, 'characterReply', ($event.target as HTMLTextAreaElement).value)"
      />
    </div>
  </div>
</template>
