<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import type { ChatCharacterInfo } from "@/types/chat";

const props = defineProps<{
  character: ChatCharacterInfo;
  sessionTitle: string;
}>();

const emit = defineEmits<{
  back: [];
  openMenu: [];
}>();

function avatarSrc(): string {
  return (
    props.character.avatar_thumbnail ||
    props.character.avatar ||
    fallbackAvatarUrl(props.character.name, 80)
  );
}
</script>

<template>
  <header
    class="z-10 grid h-15.5 shrink-0 grid-cols-3 items-center border-b bg-base-100/80 px-5 backdrop-blur-sm"
  >
    <button
      :aria-label="$t('common.goBack')"
      class="flex size-9 items-center justify-center justify-self-start rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
      @click="emit('back')"
    >
      <AppIcon name="i-lucide-arrow-left" class="size-5" />
    </button>

    <!-- Center third stays dead-centered regardless of the side zones' widths,
         so changing the side controls never shifts the heading. -->
    <div class="flex min-w-0 items-center justify-center gap-3 justify-self-center">
      <div class="relative shrink-0">
        <img
          :src="avatarSrc()"
          :alt="character.name"
          class="size-9 rounded-full object-cover ring-2 ring-primary/30"
        />
        <div
          class="absolute right-0 bottom-0 size-2.5 rounded-full border-2 border-base-100 bg-success"
        />
      </div>
      <div class="min-w-0 text-center">
        <h2
          class="truncate font-cinzel text-sm leading-tight font-semibold text-foreground"
          style="letter-spacing: 0.03em"
        >
          {{ character.name }}
        </h2>
        <p class="mt-0.5 truncate text-[0.6875rem] leading-tight text-muted-foreground">
          {{ sessionTitle }}
        </p>
      </div>
    </div>

    <div class="flex items-center justify-self-end">
      <button
        :aria-label="$t('chat.sessionMenu')"
        class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
        @click="emit('openMenu')"
      >
        <AppIcon name="i-lucide-more-horizontal" class="size-5" />
      </button>
    </div>
  </header>
</template>
