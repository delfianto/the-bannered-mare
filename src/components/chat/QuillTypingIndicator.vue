<script setup lang="ts">
defineProps<{
  characterName: string;
  characterAvatar: string;
}>();
</script>

<template>
  <div class="flex gap-3 animate-fade-in-up">
    <img
      :src="characterAvatar"
      :alt="characterName"
      class="mt-1 h-9 w-9 flex-shrink-0 rounded-full object-cover ring-1 ring-border"
    />
    <div class="rounded-2xl rounded-tl-md border border-border bg-muted px-5 py-4">
      <div class="flex items-center gap-2.5">
        <UIcon name="i-lucide-pen-tool" class="h-4 w-4 text-primary animate-quill-write" />
        <span class="text-xs italic text-muted-foreground">
          {{ characterName }} dips her quill...
        </span>
        <div class="ml-1 flex items-center gap-1">
          <span
            v-for="i in 3"
            :key="i"
            class="h-1.5 w-1.5 rounded-full bg-primary/60 animate-pulse-dot"
            :style="{ animationDelay: `${(i - 1) * 200}ms` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes quill-write {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-15deg); }
  50% { transform: rotate(0deg); }
  75% { transform: rotate(10deg); }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.1); }
}

.animate-quill-write {
  animation: quill-write 1.8s ease-in-out infinite;
}

.animate-pulse-dot {
  animation: pulse-dot 1.2s ease-in-out infinite;
}
</style>
