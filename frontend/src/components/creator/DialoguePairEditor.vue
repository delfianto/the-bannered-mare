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
  <div class="relative space-y-3 rounded-xl border bg-base-300/20 p-4">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-muted-foreground">Exchange #{{ index + 1 }}</span>
      <button
        type="button"
        class="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-error/10 hover:text-error"
        :aria-label="$t('characters.form.removeDialogue')"
        @click="emit('remove', pair.id)"
      >
        <AppIcon name="i-lucide-x" class="size-3.5" />
      </button>
    </div>

    <div class="space-y-1.5">
      <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <AppIcon name="i-lucide-user" class="size-3" />
        <span>User</span>
      </div>
      <textarea
        :value="pair.userMessage"
        placeholder='*Examines the runes.* "What do they say?"'
        rows="2"
        class="w-full resize-y rounded-lg border bg-base-100 px-3 py-2.5 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="
          emit('update', pair.id, 'userMessage', ($event.target as HTMLTextAreaElement).value)
        "
      />
    </div>

    <div class="space-y-1.5">
      <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <AppIcon name="i-lucide-bot" class="size-3" />
        <span>Character</span>
      </div>
      <textarea
        :value="pair.characterReply"
        placeholder='*Traces the inscription.* "The script speaks of a key — not of metal, but of intent."'
        rows="3"
        class="w-full resize-y rounded-lg border bg-base-100 px-3 py-2.5 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="
          emit('update', pair.id, 'characterReply', ($event.target as HTMLTextAreaElement).value)
        "
      />
    </div>
  </div>
</template>
