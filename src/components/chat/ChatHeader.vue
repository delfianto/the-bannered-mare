<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import type { ChatCharacterInfo } from "@/types/chat";

const props = defineProps<{
  character: ChatCharacterInfo;
  sessionTitle: string;
}>();

const emit = defineEmits<{
  back: [];
  rename: [title: string];
  delete: [];
}>();

const menuOpen = ref(false);
const renaming = ref(false);
const editTitle = ref("");
const confirmDelete = ref(false);
let deleteTimer: ReturnType<typeof setTimeout> | null = null;
const menuRef = ref<HTMLElement | null>(null);

function avatarSrc(): string {
  return props.character.avatar_thumbnail
    || props.character.avatar
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=80`;
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
  confirmDelete.value = false;
}

function startRename() {
  editTitle.value = props.sessionTitle;
  renaming.value = true;
  menuOpen.value = false;
}

function saveRename() {
  const trimmed = editTitle.value.trim();
  if (trimmed && trimmed !== props.sessionTitle) {
    emit("rename", trimmed);
  }
  renaming.value = false;
}

function cancelRename() {
  renaming.value = false;
}

function handleRenameKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    e.preventDefault();
    saveRename();
  } else if (e.key === "Escape") {
    cancelRename();
  }
}

function handleDelete() {
  if (confirmDelete.value) {
    emit("delete");
    menuOpen.value = false;
    confirmDelete.value = false;
  } else {
    confirmDelete.value = true;
    if (deleteTimer) clearTimeout(deleteTimer);
    deleteTimer = setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
  }
}

function handleClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false;
    confirmDelete.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside, true);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside, true);
  if (deleteTimer) clearTimeout(deleteTimer);
});
</script>

<template>
  <header
    class="z-10 flex h-[62px] flex-shrink-0 items-center justify-between border-b bg-background/80 px-5 backdrop-blur-sm"
  >
    <button
      :aria-label="$t('common.goBack')"
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
        <template v-if="renaming">
          <input
            v-model="editTitle"
            class="mt-0.5 w-full rounded border border-primary/40 bg-muted/40 px-1.5 py-0.5 text-center text-[11px] leading-tight text-foreground outline-none focus:ring-1 focus:ring-primary/30"
            autofocus
            @keydown="handleRenameKeydown"
            @blur="saveRename"
          />
        </template>
        <template v-else>
          <p class="mt-0.5 text-[11px] leading-tight text-muted-foreground">
            {{ sessionTitle }}
          </p>
        </template>
      </div>
    </div>

    <div ref="menuRef" class="relative">
      <button
        :aria-label="$t('chat.sessionMenu')"
        class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        @click="toggleMenu"
      >
        <UIcon name="i-lucide-more-horizontal" class="h-[18px] w-[18px]" />
      </button>

      <!-- Dropdown Menu -->
      <div
        v-if="menuOpen"
        class="absolute right-0 top-full mt-1 min-w-[160px] rounded-lg border bg-card py-1 shadow-lg"
      >
        <button
          class="flex w-full items-center gap-2 px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent/50"
          @click="startRename"
        >
          <UIcon name="i-lucide-pencil" class="h-4 w-4" />
          {{ $t('chat.rename') }}
        </button>
        <button
          class="flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent/50"
          :class="confirmDelete ? 'text-destructive font-medium' : 'text-destructive'"
          @click="handleDelete"
        >
          <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
          {{ confirmDelete ? $t('common.deleteConfirm') : $t('common.delete') }}
        </button>
      </div>
    </div>
  </header>
</template>
