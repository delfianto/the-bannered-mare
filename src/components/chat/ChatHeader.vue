<script setup lang="ts">
import { getAvatarUrl } from "@/api/client";
import type { ChatCharacterInfo } from "@/types/chat";

const props = defineProps<{
  character: ChatCharacterInfo;
  sessionTitle: string;
}>();

const emit = defineEmits<{
  back: [];
}>();

function avatarSrc(): string {
  if (props.character.avatar_thumbnail) return getAvatarUrl(props.character.id);
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=80`;
}
</script>

<template>
  <header
    class="z-10 flex h-[62px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-5 backdrop-blur-sm"
  >
    <button
      class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      @click="emit('back')"
    >
      <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
    </button>

    <div class="flex items-center gap-3">
      <div class="relative">
        <img
          :src="avatarSrc()"
          :alt="character.name"
          class="h-9 w-9 rounded-full object-cover ring-2 ring-primary/30"
        />
        <div
          class="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-background bg-emerald-500"
        />
      </div>
      <div class="text-center">
        <h2
          class="font-cinzel text-sm font-semibold leading-tight text-foreground"
          style="letter-spacing: 0.03em"
        >
          {{ character.name }}
        </h2>
        <p class="mt-0.5 text-[11px] leading-tight text-muted-foreground">
          {{ sessionTitle }}
        </p>
      </div>
    </div>

    <button
      class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
    >
      <UIcon name="i-lucide-more-horizontal" class="h-[18px] w-[18px]" />
    </button>
  </header>
</template>
